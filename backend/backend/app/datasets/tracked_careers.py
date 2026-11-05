"""Graduates per career and institution, from the official files of each country.

- Chile (Mi Futuro): generic careers per institution, and programs that match a topic, by original
  name. The topics and their patterns are in analytics.yaml -> tracked_careers.file.
- Uruguay (MEC yearbooks): degrees per institution, one yearbook per year.
- Argentina (DIU yearbooks): disciplines per institution, one yearbook per year.

The links come from the official pages, through each file's dataset profile. The files are read
again when a link or the settings change. Institution sums are checked against what each source
publishes, and nothing loads if they do not match. Totals go to hecho_egresados, and what changes or
disappears to data_revisions.
"""
import hashlib
import io
import json
import re
import zipfile
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import openpyxl
import yaml
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics.graduate_trends_run import career_name
from app.connectors.http import download_sync
from app.core.config import settings
from app.core.config_files import analytics_params, app_config, sources
from app.datasets.ingest import DatasetError, _format_alert, find_download_links, store_file
from app.datasets.profiles import DownloadConf, normalize_text, profiles
from app.datasets.reader import Issue, ReadReport
from app.datasets.universities import (
    _DirectInput,
    _source_ids,
    clean_name,
    normalized_name,
    to_number,
)
from app.ingestion.revisions import record_changes
from app.models import DatasetFile, FactEgresados, IngestionRun, Source

KEY = ["pais", "nivel_granularidad", "carrera_objetivo", "institucion", "nivel", "sexo", "anio"]


@dataclass
class OfficialFile:
    role: str
    path: Path
    release: str | None


def tracked_definitions(conf: dict) -> tuple[list[dict], str]:
    """(careers, checksum of the patterns, name files and settings): a change means reading the
    data again."""
    content = (settings.config_dir / conf["file"]).read_bytes()
    names = [analytics_params("universities")["names_file"],
             analytics_params("graduate_trends")["countries"]["URY"]["names_file"],
             conf["argentina"]["names_file"]]
    digest = hashlib.sha256(content + json.dumps(conf, sort_keys=True).encode())
    for path in names:
        digest.update((settings.config_dir / path).read_bytes())
    return yaml.safe_load(content)["careers"], digest.hexdigest()


def matching_topic(program: str, careers: list[dict]) -> dict | None:
    """The first topic in the file whose pattern the program's name matches."""
    name = normalize_text(program)
    return next((c for c in careers if re.search(c["patron"], name)), None)


def institution_name(country: str, published: str) -> str:
    """The normalized name of a university; other institutions stay as published."""
    name = clean_name(published)
    return normalized_name(country, name, analytics_params("universities")) or name


def _row(country: str, career: str | None, institution: str | None, level: str, year: int, value: float,
         source: str, granularity: str, topic: str | None = None, sector: str | None = None,
         sex: str | None = None) -> dict:
    return {"pais": country, "carrera_objetivo": career, "institucion": institution, "nivel": level,
            "anio": year, "valor": value, "fuente_id": source, "nivel_granularidad": granularity,
            "carrera_id": topic, "sector": sector, "sexo": sex, "es_observado": True}


def _control(name: str, year: int, value: float, expected: float | None, tolerance: float) -> dict:
    ok = bool(expected) and abs(value / expected - 1) <= tolerance or (not expected and not value)
    return {"control": name, "anio": year, "valor": value, "esperado": expected, "ok": ok}


def program_totals(rows: Iterable, careers: list[dict], conf: dict) -> list[dict]:
    """Chile. rows: (year label, value, program, level, generic career, institution, *graduates per
    sex, in the order of sex_columns). One row per program with a topic, institution, level and
    year, as published; and, for the levels generic careers count, one per generic career,
    institution and year, and one per generic career, sex and year."""
    topics: dict[str, dict | None] = {}
    institutions: dict[str, str] = {}
    totals: dict[tuple, float] = {}
    by_sex: dict[tuple, float] = {}
    sexes = list(conf["sex_columns"])
    for year_label, value, program, level, generic, institution, *per_sex in rows:
        if not isinstance(value, (int, float)) or not value or not institution:
            continue
        if institution not in institutions:
            institutions[institution] = institution_name("CHL", institution)
        name = institutions[institution]
        year = int(re.search(r"\d{4}", str(year_label)).group(0))
        level = str(level).strip()
        if program not in topics:
            topics[program] = matching_topic(program, careers) if program else None
        topic = topics[program]
        if topic:
            key = (conf["granularity"], topic["id"], clean_name(program), topic["sector"], name, level, year)
            totals[key] = totals.get(key, 0.0) + float(value)
        if generic and level in conf["generic_levels"]:
            key = (conf["institution_granularity"], None, clean_name(generic), None, name, level, year)
            totals[key] = totals.get(key, 0.0) + float(value)
            for sex, count in zip(sexes, per_sex, strict=False):
                if isinstance(count, (int, float)) and count:
                    key = (clean_name(generic), level, sex, year)
                    by_sex[key] = by_sex.get(key, 0.0) + float(count)
    return [_row(conf["country"], title, name, level, year, value, conf["source"], granularity, cid, sector)
            for (granularity, cid, title, sector, name, level, year), value in totals.items()] + [
        _row(conf["country"], career, None, level, year, value, conf["source"], conf["sex_granularity"], sex=sex)
        for (career, level, sex, year), value in by_sex.items()]


def read_chile(path: Path, careers: list[dict], conf: dict) -> list[dict]:
    rows = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0].iter_rows(
        values_only=True)
    header = [str(c).strip() for c in next(rows)]
    columns = [header.index(c) for c in [*conf["columns"], *conf["sex_columns"].values()]]
    return program_totals(((r[i] for i in columns) for r in rows), careers, conf)


def read_uruguay_yearbook(path: Path, year: int, conf: dict) -> tuple[list[dict], list[dict]]:
    """One MEC yearbook. Institution, faculty, campus and program rows share one column, and only
    programs are not bold: each program belongs to the last institution row above it."""
    trends = analytics_params("graduate_trends")
    universities = analytics_params("universities")
    layout = universities["ury"]
    column = layout["graduates_column"]
    book = openpyxl.load_workbook(path, data_only=True)
    named = {w.title.strip(): w for w in book.worksheets if w.title.strip() in layout["sheets"]}
    totals, published, controls, by_sex = {}, {}, [], {}
    for sheet, ws in named.items():
        patterns = [i for i in layout["institutions"] if i["sheet"] == sheet]
        current = None
        for row in ws.iter_rows():
            cell = row[0]
            if cell.value in (None, ""):
                continue
            name = clean_name(cell.value)
            found = next((i["name"] for i in patterns if re.search(i["pattern"], name)), None)
            if found is None and sheet == layout["institute_sheet"] and re.search(layout["institute_pattern"], name):
                found = name
            value = row[column].value if len(row) > column else None
            if found:
                current = institution_name("URY", found)
                published[current] = to_number(value, universities) or 0.0
            elif current and not cell.font.b:
                number = to_number(value, universities)
                if number:
                    career = career_name(name, trends["countries"]["URY"], trends)
                    key = (career, current)
                    totals[key] = totals.get(key, 0.0) + number
                    for sex, sex_column in conf["uruguay"]["sex_columns"].items():
                        count = to_number(row[sex_column].value, universities) if len(row) > sex_column else None
                        if count:
                            by_sex[(career, sex)] = by_sex.get((career, sex), 0.0) + count
    rows = [_row("URY", career, institution, conf["uruguay"]["level"], year, value,
                 conf["uruguay"]["source"], conf["institution_granularity"])
            for (career, institution), value in totals.items()]
    rows += [_row("URY", career, None, conf["uruguay"]["level"], year, value, conf["uruguay"]["source"],
                  conf["sex_granularity"], sex=sex) for (career, sex), value in by_sex.items()]
    for institution, expected in published.items():
        added = sum(v for (_, i), v in totals.items() if i == institution)
        controls.append(_control(f"URY {institution}", year, added, expected, conf["total_tolerance"]))
    return rows, controls


def argentine_disciplines(conf: dict) -> dict[str, str]:
    """Normalized discipline name -> the name the series uses: the careers of the crosswalk, plus
    the other ways the yearbooks write them (argentina.names_file)."""
    trends = analytics_params("graduate_trends")
    crosswalk = analytics_params("skill_gaps")["crosswalks"]["ARG"]
    known = {normalize_text(name): name
             for name in yaml.safe_load((settings.config_dir / crosswalk).read_bytes())["careers"]}
    table = yaml.safe_load((settings.config_dir / conf["argentina"]["names_file"]).read_bytes())
    for form, final in (table.get("formas") or {}).items():
        known[normalize_text(form)] = final
    for skipped in trends["skip_careers"]:
        known.pop(skipped, None)
    return known


def _read_discipline_table(rows: list, conf: dict, known: dict[str, str]
                           ) -> tuple[dict[tuple, float], float, float, set[str]]:
    """One table: an institution per row and, per discipline, a column of graduates. Returns
    ({(career, institution): graduates}, sum found, the table's own total, unknown columns)."""
    settings_ = conf["argentina"]
    universities = analytics_params("universities")
    kinds = {k.upper() for k in settings_["value_kinds"]}
    skip = re.compile(settings_["skip_names_pattern"], re.I)
    k = next(i for i, r in enumerate(rows[:settings_["header_rows"]])
             if any(c is not None and str(c).strip().upper() in kinds for c in r))
    names, row_kinds = rows[k - 1], rows[k]
    columns, unknown, current, total_column = [], set(), None, None
    for j, kind in enumerate(row_kinds):
        if j < len(names) and names[j]:
            current = clean_name(names[j])
        if kind is None or str(kind).strip().upper() not in kinds or not current:
            continue
        if skip.search(current):
            total_column = j if total_column is None else total_column
            continue
        plain = normalize_text(re.sub(universities["footnote_pattern"], "", current))
        if plain in known:
            columns.append((j, known[plain]))
        elif plain not in settings_["not_disciplines"]:
            unknown.add(current)
    # the only column with text in the body: its heading row does not say which it is
    name_column = Counter(i for r in rows[k + 1:] for i, c in enumerate(r)
                          if isinstance(c, str) and c.strip() not in universities["missing_text"]
                          ).most_common(1)[0][0]
    totals: dict[tuple, float] = {}
    expected, found = None, 0.0
    for row in rows[k + 1:]:
        values = [(career, to_number(row[j], universities) if j < len(row) else None) for j, career in columns]
        if not any(v is not None for _, v in values):
            continue
        name = row[name_column] if len(row) > name_column else None
        if expected is None:  # the first row with figures is the table's total
            # its own total column when it has one: some total rows leave disciplines blank
            own = to_number(row[total_column], universities) if total_column is not None else None
            expected = own if own is not None else sum(v or 0 for _, v in values)
            continue
        if name is None or skip.search(clean_name(name)):
            continue
        institution = institution_name("ARG", name)
        for career, value in values:
            if value:
                totals[(career, institution)] = totals.get((career, institution), 0.0) + value
                found += value
    return totals, found, expected or 0.0, unknown


def _sex_columns(rows: list, conf: dict) -> dict[str, int] | None:
    """{sex: column} of graduates in a table of "género": the labels below the group "Egresados"."""
    argentina = conf["argentina"]
    for i, row in enumerate(rows[:argentina["header_rows"]]):
        group = next((j for j, c in enumerate(row) if isinstance(c, str)
                      and re.search(argentina["sex_group_pattern"], clean_name(c), re.I)), None)
        if group is None or i + 1 >= len(rows):
            continue
        labels = rows[i + 1]
        found = {}
        for sex, pattern in argentina["sex_labels"].items():
            found[sex] = next((j for j in range(group, min(group + 4, len(labels)))
                               if isinstance(labels[j], str) and re.search(pattern, clean_name(labels[j]), re.I)), None)
        if all(v is not None for v in found.values()):
            return found
    return None


def read_argentina_sex_totals(path: Path, conf: dict, members: str, level: str, source: str,
                              release: int | None = None) -> tuple[list[dict], list[str]]:
    """Graduates by sex for the whole country: the first row with figures of each table, one for
    public and one for private institutions. A yearbook without those tables gives a warning."""
    argentina = conf["argentina"]
    universities = analytics_params("universities")
    title_re = re.compile(argentina["sex_title_pattern"], re.I)
    exclude_re = re.compile(argentina["sex_exclude_pattern"], re.I)
    member_re = re.compile(members, re.I)
    totals: dict[tuple[int, str], float] = {}
    tables = 0
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name = info.filename.rsplit("/", 1)[-1]
            if not member_re.search(name) or not name.lower().endswith(".xlsx"):
                continue
            book = openpyxl.load_workbook(io.BytesIO(archive.read(info)), read_only=True, data_only=True)
            for ws in book.worksheets:
                rows = [tuple(r) for r in ws.iter_rows(max_row=argentina["header_rows"] + 3, values_only=True)]
                title = clean_name(" ".join(str(c) for r in rows[:argentina["header_rows"]] for c in r
                                            if isinstance(c, str)))
                if not title_re.search(title) or exclude_re.search(title):
                    continue
                columns = _sex_columns(rows, conf)
                if columns is None:
                    continue
                year = int(re.search(argentina["year_pattern"], title).group(1))
                if release is not None and year != release:
                    continue
                first = next((r for r in rows if isinstance(r[columns["F"]] if len(r) > columns["F"] else None,
                                                            (int, float))), None)
                if first is None:
                    continue
                tables += 1
                for sex, column in columns.items():
                    totals[(year, sex)] = totals.get((year, sex), 0.0) + (to_number(first[column], universities) or 0.0)
    warnings = [] if tables == 2 else [f"{path.name}: {tables} cuadros de sexo, se esperaban 2"]
    return [_row("ARG", None, None, level, year, value, source, conf["sex_granularity"], sex=sex)
            for (year, sex), value in totals.items()], warnings


def read_argentina_csv_sex_totals(path: Path, conf: dict, spec: dict, level: str, source: str) -> list[dict]:
    universities = analytics_params("universities")
    totals: dict[str, float] = {}
    with zipfile.ZipFile(path) as archive:
        for member in spec["sex_tables"]:
            management, name = member.split("|")
            lines = archive.read(spec["folder"].format(management=management) + name).decode("utf-8-sig").splitlines()
            first = dict(zip(lines[0].split("|"), lines[1].split("|"), strict=False))
            for sex, column in spec["sex_columns"].items():
                totals[sex] = totals.get(sex, 0.0) + (to_number(first[column], universities) or 0.0)
    return [_row("ARG", None, None, level, spec["year"], value, source, conf["sex_granularity"], sex=sex)
            for sex, value in totals.items()]


def _yearly_control(year: int, added: float, expected: float, conf: dict) -> dict:
    """All of a year's tables against their own totals: one table's subtotal can have a typo, and
    a year the source publishes without some disciplines is listed in known_gaps."""
    check = _control(f"ARG {year}", year, added, expected, conf["total_tolerance"])
    if year in conf["argentina"]["known_gaps"]:
        check["ok"] = True
    return check


def read_argentina_yearbook(path: Path, conf: dict, members: str, level: str, source: str,
                            release: int | None = None) -> tuple[list[dict], list[dict], set[str]]:
    """A DIU yearbook in spreadsheets: its discipline tables, for the yearbook's own year."""
    title_re = re.compile(conf["argentina"]["title_pattern"], re.I)
    member_re = re.compile(members, re.I)
    known = argentine_disciplines(conf)
    totals, unknown = {}, set()
    sums: dict[int, list[float]] = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name = info.filename.rsplit("/", 1)[-1]
            if not member_re.search(name) or not name.lower().endswith(".xlsx"):
                continue
            book = openpyxl.load_workbook(io.BytesIO(archive.read(info)), read_only=True, data_only=True)
            for ws in book.worksheets:
                rows = [tuple(r) for r in ws.iter_rows(values_only=True)]
                # titles may be split across cells
                title = clean_name(" ".join(str(c) for r in rows[:conf["argentina"]["header_rows"]]
                                            for c in r if isinstance(c, str)))
                if not title_re.search(title):
                    continue
                year = int(re.search(conf["argentina"]["year_pattern"], title).group(1))
                if release is not None and year != release:
                    raise ValueError(f"{path.name}: {ws.title} es de {year}, se esperaba {release}")
                found, added, expected, others = _read_discipline_table(rows, conf, known)
                unknown |= others
                for (career, institution), value in found.items():
                    key = (career, institution, year)
                    totals[key] = totals.get(key, 0.0) + value
                year_sum = sums.setdefault(year, [0.0, 0.0])
                year_sum[0] += added
                year_sum[1] += expected
    controls = [_yearly_control(year, added, expected, conf) for year, (added, expected) in sums.items()]
    if release is not None and not totals:
        raise ValueError(f"{path.name}: no se encontraron cuadros por disciplina")
    return [_row("ARG", career, institution, level, year, value, source, conf["institution_granularity"])
            for (career, institution, year), value in totals.items()], controls, unknown


def read_argentina_csv_yearbook(path: Path, conf: dict, spec: dict, level: str, source: str
                                ) -> tuple[list[dict], list[dict], set[str]]:
    """A DIU yearbook in CSV. Each discipline is a column e_<name>, which the private tables also
    abbreviate. Two private tables have no name column: their rows follow the order of `names_table`,
    which is checked against its figures."""
    table = yaml.safe_load((settings.config_dir / conf["argentina"]["names_file"]).read_bytes())
    columns = table["columnas_csv"]
    universities = analytics_params("universities")
    skip = re.compile(conf["argentina"]["skip_names_pattern"], re.I)
    totals, unknown = {}, set()
    found_total, expected_total = 0.0, 0.0
    with zipfile.ZipFile(path) as archive:
        def read(member: str) -> list[dict]:
            text = archive.read(spec["folder"].format(management=member.split("|")[0]) + member.split("|")[1])
            lines = text.decode("utf-8-sig").splitlines()
            header = lines[0].split("|")
            return [dict(zip(header, line.split("|"), strict=False)) for line in lines[1:] if line.strip()]

        for group in spec["tables"]:
            order = [r[spec["name_column"]] for r in read(group["names_table"])]
            for member in group["members"]:
                records = read(member)
                if len(records) != len(order):
                    raise ValueError(f"{member}: {len(records)} filas, se esperaban {len(order)}")
                wanted = [c for c in records[0] if c.startswith(spec["graduates_prefix"])]
                expected = None
                for name, record in zip(order, records, strict=True):
                    values = []
                    for column in wanted:
                        if column in columns:
                            values.append((columns[column], to_number(record.get(column), universities)))
                        elif column not in spec["not_disciplines"]:
                            unknown.add(column)
                    if expected is None:
                        expected = to_number(record.get(spec["total_column"]), universities) or 0.0
                        continue
                    if skip.search(clean_name(name)):
                        continue
                    institution = institution_name("ARG", name)
                    for career, value in values:
                        if value:
                            key = (career, institution, spec["year"])
                            totals[key] = totals.get(key, 0.0) + value
                            found_total += value
                expected_total += expected or 0.0
    controls = [_yearly_control(spec["year"], found_total, expected_total, conf)]
    return [_row("ARG", career, institution, level, year, value, source, conf["institution_granularity"])
            for (career, institution, year), value in totals.items()], controls, unknown


def read_all(files: list[OfficialFile], careers: list[dict], conf: dict
             ) -> tuple[list[dict], list[dict], list[str]]:
    """(rows, controls, warnings) of every file."""
    rows, controls, unknown, warnings = [], [], set(), []
    argentina = conf["argentina"]
    profile = profiles()[argentina["profile"]]
    level, source = profile.discipline_tables.level, profile.source
    yearbooks = {str(y["release"]): y for y in argentina["yearbooks"]}
    for file in files:
        if file.role == "chl":
            rows += read_chile(file.path, careers, conf)
        elif file.role == "ury":
            found, checks = read_uruguay_yearbook(file.path, int(file.release), conf)
            rows += found
            controls += checks
        elif file.role == "arg":
            found, checks, others = read_argentina_yearbook(
                file.path, conf, profile.discipline_tables.members_pattern, level, source)
            rows += found
            controls += checks
            unknown |= others
            sexes, notes = read_argentina_sex_totals(file.path, conf, profile.discipline_tables.members_pattern, level, source)
            rows += sexes
            warnings += notes
        elif file.role == "arg_history":
            spec = yearbooks[file.release]
            if "csv" in spec:
                csv_spec = {**spec["csv"], "year": spec["release"]}
                found, checks, others = read_argentina_csv_yearbook(file.path, conf, csv_spec, level, source)
                rows += read_argentina_csv_sex_totals(file.path, conf, csv_spec, level, source)
            else:
                found, checks, others = read_argentina_yearbook(file.path, conf, spec["members"], level, source, spec["release"])
                sexes, notes = read_argentina_sex_totals(file.path, conf, spec["members"], level, source, spec["release"])
                rows += sexes
                warnings += notes
            rows += found
            controls += checks
            unknown |= others
    if unknown:
        warnings.append(f"Disciplinas no reconocidas: {', '.join(sorted(unknown))}")
    return rows, controls, warnings


def load_tracked(session: Session, rows: list[dict], source_ids: dict[str, int], run_id: int | None,
                 conf: dict) -> int:
    """Replace the stored totals, logging what changes or disappears. Returns the revisions logged."""
    kinds = [conf["granularity"], conf["institution_granularity"], conf["sex_granularity"]]
    scope = FactEgresados.nivel_granularidad.in_(kinds)
    stored = session.scalars(select(FactEgresados).where(scope)).all()
    revisions = 0
    for code, source_id in source_ids.items():
        old = {tuple(getattr(o, k) for k in KEY): (o.valor, None) for o in stored if o.fuente_id == code}
        new = {tuple(r[k] for k in KEY): r["valor"] for r in rows if r["fuente_id"] == code}
        revisions += record_changes(session, FactEgresados.__tablename__, source_id, run_id, KEY, old, new,
                                    removals=True)
    session.execute(delete(FactEgresados).where(scope))
    session.flush()
    session.add_all([FactEgresados(**r) for r in rows])
    session.flush()
    return revisions


def _official_links(conf: dict) -> list[tuple[str, int, str, str | None]]:
    """(role, max bytes, url, release) of every file the official pages link now."""
    out = []
    for role, code in (("chl", conf["profile"]), ("arg", conf["argentina"]["profile"]),
                       ("ury", conf["uruguay"]["profile"])):
        profile = profiles()[code]
        out += [(role, profile.download.max_bytes, link.url, link.release)
                for link in find_download_links(profile)]
    argentina = conf["argentina"]
    for spec in argentina["yearbooks"]:
        source = _DirectInput(argentina["landing_page"], DownloadConf(
            link_pattern=spec["link_pattern"], allowed_hosts=argentina["allowed_hosts"],
            max_bytes=argentina["max_bytes"]))
        out += [("arg_history", argentina["max_bytes"], link.url, str(spec["release"]))
                for link in find_download_links(source)]
    return out


def run_tracked_careers_source(session: Session, source_code: str,
                               run: IngestionRun) -> tuple[int, list[str]]:
    """Download, check and load. Returns (rows loaded, warnings); (0, []) if nothing changed."""
    conf = analytics_params("tracked_careers")
    careers, checksum = tracked_definitions(conf)
    links = _official_links(conf)
    last = session.scalars(select(DatasetFile).where(
        DatasetFile.profile_code == conf["dataset_code"], DatasetFile.status == "loaded")).all()
    if last and {d.url for d in last} == {url for _, _, url, _ in links} \
            and all(d.report.get("patterns") == checksum for d in last):
        return 0, []
    source = session.scalar(select(Source).where(Source.source_code == source_code))
    datasets_conf = app_config().datasets
    files, datasets = [], []
    for role, max_bytes, url, release in links:
        content = download_sync(url, max_bytes, {"User-Agent": sources().http.user_agent})
        name = Path(urlparse(url).path).name
        path, sha = store_file(content, datasets_conf.path(datasets_conf.raw_dir) / source_code, name)
        dataset = DatasetFile(
            profile_code=conf["dataset_code"], source_id=source.source_id, origin="download", file_name=name,
            url=url, release=release, sha256=sha, size_bytes=len(content), stored_path=str(path),
            status="validated", report={"patterns": checksum}, created_at=datetime.now(UTC), run_id=run.run_id)
        session.add(dataset)
        datasets.append(dataset)
        files.append(OfficialFile(role, path, release))
    session.flush()

    def refuse(reason: str) -> DatasetError:
        for dataset in datasets:
            dataset.status = "format_changed"
        _format_alert(session, datasets[0], source, ReadReport(errors=[Issue(reason)]))
        return DatasetError(f"{conf['dataset_code']}: {reason}")

    try:
        rows, controls, warnings = read_all(files, careers, conf)
    except (KeyError, IndexError, ValueError, StopIteration, TypeError, AttributeError,
            zipfile.BadZipFile) as exc:
        raise refuse(f"{type(exc).__name__}: {exc}") from exc
    failed = [c for c in controls if not c["ok"]]
    if failed:
        first = failed[0]
        raise refuse(f"{len(failed)} controles no coinciden, p. ej. {first['control']} {first['anio']}: "
                     f"{first['valor']} contra {first['esperado']}")
    source_ids = _source_ids(session, {r["fuente_id"] for r in rows})
    load_tracked(session, rows, source_ids, run.run_id, conf)
    for previous in last:
        previous.status = "replaced"
    for dataset in datasets:
        dataset.status, dataset.loaded_at = "loaded", datetime.now(UTC)
    datasets[0].records = len(rows)
    found = {r["carrera_id"] for r in rows}
    empty = sorted(c["nombre"] for c in careers if c["id"] not in found)
    if empty:
        warnings.append(f"Temas de seguimiento sin programas: {', '.join(empty)}")
    return len(rows), warnings
