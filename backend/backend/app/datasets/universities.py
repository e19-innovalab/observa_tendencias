"""Graduates per university and rankings, built on each run from the publishers' official files.

The links come from the official pages (analytics.yaml -> universities.inputs); nothing is read from
local copies. Files are downloaded only when a link changes. The data loads only if every file
keeps its format and the institution totals match what each source publishes; otherwise nothing
changes and the reason stays in dataset_files and in an alert.
"""
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import openpyxl
import pandas as pd
import yaml
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.connectors.http import download_sync
from app.core.config import settings
from app.core.config_files import analytics_params, app_config, sources
from app.datasets.ingest import DatasetError, _format_alert, find_download_links, store_file
from app.datasets.profiles import DownloadConf, profiles
from app.datasets.reader import Issue, ReadReport
from app.ingestion.revisions import record_changes
from app.models import (
    DatasetFile,
    FactInstitucionesEgresados,
    IngestionRun,
    RankingUniversidadesNacional,
    RankingUniversidadesRegional,
    Source,
)

DATASET = FactInstitucionesEgresados.__tablename__
KEY = ["pais", "fuente_id", "institucion", "anio"]
ODS_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"


@dataclass
class _DirectInput:
    """A file not covered by a dataset profile: the fields find_download_links needs."""
    landing_page: str
    download: DownloadConf


@dataclass
class OfficialFile:
    role: str
    path: Path
    release: str | None


def to_number(value, conf: dict) -> float | None:
    """Published number or None; '-', 's/d' and the like mean there is no data."""
    if value is None or str(value).strip() in conf["missing_text"]:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    number = pd.to_numeric(str(value).strip().replace(".", "").replace(",", "."), errors="coerce")
    return None if pd.isna(number) else float(number)


def clean_name(value) -> str:
    return re.sub(r"\s+", " ", str(value).replace("*", "")).strip()


def _control(name: str, year, value: float, expected: float | None, conf: dict) -> dict:
    ok = bool(expected) and abs(value / expected - 1) <= conf["total_tolerance"]
    return {"control": name, "anio": int(year), "valor": value, "esperado": expected,
            "resultado": "ok" if ok else conf["control_pending"]}


def _row(country: str, name: str, management: str, kind: str | None, year: int, value: float,
         source: str, observed: bool = True) -> dict:
    return {"pais": country, "publicado": name, "tipo_gestion": management, "tipo_institucion": kind,
            "anio": int(year), "graduados": value, "fuente_id": source, "es_observado": observed}


def tidy_yearbook_table(rows: list[list], management: str, conf: dict) -> list[dict]:
    """One row per institution and year from an 'Institución | 2014 | 2015 ...' table. The 'Total'
    rows are not institutions: each one names the kind of the institutions below it."""
    records, kind = [], None
    years = rows[0]
    for row in rows[1:]:
        name = clean_name(row[0])
        if not name or name == "nan":
            continue
        if name.lower().startswith("total"):
            lowered = name.lower()
            if "institutos" in lowered:
                kind = conf["institute_type"]
            elif "universidades" in lowered:
                kind = conf["ranked_institution_type"]
            continue
        for year, value in zip(years[1:], row[1:], strict=False):
            number = to_number(value, conf)
            if year is not None and number is not None:
                records.append(_row("ARG", name, management, kind, year, number,
                                    conf["arg"]["source"]))
    return records


def read_latest_yearbook(path: Path, conf: dict) -> dict[str, list[list]]:
    """Graduates by institution, per management, from the latest DIU yearbook."""
    tables = {}
    archive = zipfile.ZipFile(path)
    for table in conf["arg"]["latest_tables"]:
        name = next(n for n in archive.namelist() if n.startswith(table["member_prefix"]))
        book = openpyxl.load_workbook(io.BytesIO(archive.read(name)), read_only=True, data_only=True)
        rows = list(book[table["sheet"]].iter_rows(values_only=True))
        title = next(str(c) for r in rows for c in r if c)
        if conf["arg"]["title_word"] not in title.lower():
            raise ValueError(f"{table['sheet']}: no es el cuadro de egresados: {title}")
        start = next(i for i, r in enumerate(rows)
                     if any(str(c).split(".")[0].isdigit() and 2000 < float(c) < 2100
                            for c in r if c is not None))
        columns = [i for i, c in enumerate(rows[start]) if str(c).split(".")[0].isdigit()]
        header = [None] + [int(str(rows[start][i]).split(".")[0]) for i in columns]
        first = next(i for i, c in enumerate(rows[start + 1]) if c is not None)
        body = [[r[first]] + [r[i] for i in columns] for r in rows[start + 1:]
                if r[first] is not None
                and not str(r[first]).startswith(tuple(conf["arg"]["footnote_starts"]))]
        tables[table["management"]] = [header] + body
    return tables


def read_argentina(latest: Path, history: Path, conf: dict) -> tuple[list[dict], list[dict]]:
    """The latest yearbook; older years only from the earlier yearbook. Sums are checked against
    the totals each yearbook prints, and the overlap years against each other."""
    rows, controls = [], []
    newest: dict[str, list[dict]] = {}
    for management, table in read_latest_yearbook(latest, conf).items():
        tidy = tidy_yearbook_table(table, management, conf)
        newest[management] = tidy
        rows += tidy
        total = next(r for r in table[1:] if clean_name(r[0]).startswith("Total Instituciones"))
        for year, published in zip(table[0][1:], total[1:], strict=False):
            added = sum(r["graduados"] for r in tidy if r["anio"] == year)
            controls.append(_control(f"ARG {management}: suma de instituciones", year, added,
                                     to_number(published, conf), conf))
    archive = zipfile.ZipFile(history)
    for table in conf["arg"]["history_tables"]:
        frame = pd.read_csv(io.BytesIO(archive.read(table["member"])), sep="|", encoding="utf-8")
        year_columns = [c for c in frame.columns if re.fullmatch(r"_\d{4}", c)]
        values = [[None] + [int(c[1:]) for c in year_columns]] \
            + frame[[conf["arg"]["history_name_column"]] + year_columns].values.tolist()
        tidy = tidy_yearbook_table(values, table["management"], conf)
        latest_rows = newest[table["management"]]
        first_year = min(r["anio"] for r in latest_rows)
        for year in sorted({r["anio"] for r in tidy} & {r["anio"] for r in latest_rows}):
            controls.append(_control(
                f"ARG {table['management']}: anuario anterior contra el último", year,
                sum(r["graduados"] for r in tidy if r["anio"] == year),
                sum(r["graduados"] for r in latest_rows if r["anio"] == year), conf))
        rows += [r for r in tidy if r["anio"] < first_year]
    return rows, controls


def read_chile(path: Path, conf: dict) -> list[dict]:
    """Degrees by university, added up across campuses and programs."""
    c = conf["chl"]
    rows = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0].iter_rows(
        values_only=True)
    header = [str(cell).strip() for cell in next(rows)]
    keep = [header.index(col) for col in c["columns"].values()]
    frame = pd.DataFrame([[r[i] for i in keep] for r in rows], columns=list(c["columns"]))
    frame = frame[(frame.tipo == c["institution_type"]) & (frame.nivel == conf["levels"]["CHL"])]
    frame["anio"] = frame.anio.astype(str).str.extract(r"(\d{4})")[0].astype(int)
    frame["egresados"] = pd.to_numeric(frame.egresados, errors="coerce").fillna(0)
    frame["institucion"] = frame.institucion.map(clean_name)
    grouped = frame.groupby(["institucion", "gestion", "anio"], as_index=False).egresados.sum()
    return [_row("CHL", r.institucion, r.gestion, conf["ranked_institution_type"], r.anio,
                 float(r.egresados), c["source"]) for r in grouped.itertuples()]


def read_udelar(path: Path, conf: dict) -> list[dict]:
    """UdelaR's own series, from the university total row of the spreadsheet."""
    c = conf["udelar"]
    rows = []
    for row in ET.fromstring(zipfile.ZipFile(path).read("content.xml")).iter(ODS_TABLE + "table-row"):
        cells = []
        for cell in row:
            repeat = int(cell.get(ODS_TABLE + "number-columns-repeated", "1"))
            cells.extend(["".join(cell.itertext()).strip()] * min(repeat, c["max_repeat"]))
        rows.append(cells)
    header = next(r for r in rows if r and r[0].startswith(c["header_starts"]))
    total = next(r for r in rows if r and r[0] == c["total_row"])
    return [_row("URY", c["name"], c["management"], conf["ranked_institution_type"], int(year),
                 to_number(value, conf), c["source"])
            for year, value in zip(header[1:], total[1:], strict=False) if year.isdigit()]


def read_uruguay(files: list[OfficialFile], udelar: list[dict],
                 conf: dict) -> tuple[list[dict], list[dict]]:
    """Each year from that year's MEC yearbook, whose institution, faculty and program rows share
    one column. UdelaR's main figure is its own series: the yearbook's is preliminary."""
    c = conf["ury"]
    records, controls = [], []
    series = {r["anio"]: r["graduados"] for r in udelar}
    column = c["graduates_column"]
    for file in files:
        year = int(file.release)
        book = openpyxl.load_workbook(file.path, read_only=True, data_only=True)
        sheets = {w.title.strip(): list(w.iter_rows(values_only=True)) for w in book.worksheets
                  if w.title.strip() in c["sheets"]}
        found = []
        for inst in c["institutions"]:
            row = next((r for r in sheets[inst["sheet"]]
                        if r[0] and re.search(inst["pattern"], clean_name(r[0]))), None)
            if row is not None:
                found.append((inst["sheet"], inst["management"], conf["ranked_institution_type"],
                              inst["name"], to_number(row[column], conf)))
        for row in sheets[c["institute_sheet"]]:
            if row[0] and re.search(c["institute_pattern"], clean_name(row[0])) \
                    and row[column] is not None:
                name = clean_name(row[0])
                management = "publica" if re.search(c["public_institute_pattern"], name) else "privada"
                found.append((c["institute_sheet"], management, conf["institute_type"], name,
                              to_number(row[column], conf)))
        for sheet, rows in sheets.items():
            total = next(r for r in rows if r[0] and re.fullmatch(c["total_pattern"], clean_name(r[0])))
            added = sum(v for s, _, _, _, v in found if s == sheet and v is not None)
            controls.append(_control(f"URY {sheet}: suma de instituciones", year, added,
                                     to_number(total[column], conf), conf))
        records += [_row("URY", name, management, kind, year, value, c["source"])
                    for _, management, kind, name, value in found
                    if value is not None and name != conf["udelar"]["name"]]
        if year not in series:
            raise ValueError(f"La serie de UdelaR no tiene el año {year}")
    return records + udelar, controls


@lru_cache
def university_names() -> dict:
    conf = analytics_params("universities")
    with (settings.config_dir / conf["names_file"]).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalized_name(country: str, published: str, conf: dict) -> str | None:
    """The name in the names file; footnote marks are removed unless the marked form is listed."""
    names = university_names().get(country, {})
    if published in names:
        return names[published]
    return names.get(re.sub(conf["footnote_pattern"], "", published).strip())


def apply_names(rows: list[dict], conf: dict) -> tuple[list[dict], list[str]]:
    """One row per institution, source and year under its normalized name, adding up the forms the
    source published. Returns the rows and the published names missing from the names file."""
    missing, merged = set(), {}
    for row in rows:
        name = normalized_name(row["pais"], row["publicado"], conf)
        if name is None:
            missing.add(f"{row['pais']}: {row['publicado']}")
            name = row["publicado"]
        key = (row["pais"], row["fuente_id"], name, row["anio"])
        if key in merged:
            merged[key]["graduados"] += row["graduados"]
            continue
        merged[key] = {k: v for k, v in row.items() if k != "publicado"} | {
            "institucion": name, "sector": conf["sector_label"]}
    return list(merged.values()), sorted(missing)


def ranking_rows(rows: list[dict], conf: dict) -> tuple[list[dict], list[dict]]:
    """(national, regional) rows: universities with the most graduates, which measures size and
    not quality. Nationally each country's latest year; regionally the latest year all share."""
    universities = [r for r in rows if r["tipo_institucion"] == conf["ranked_institution_type"]]
    years: dict[str, set[int]] = {}
    for r in universities:
        years.setdefault(r["pais"], set()).add(r["anio"])
    top = conf["top_n"]

    def common(r: dict) -> dict:
        return {"institucion": r["institucion"], "pais": r["pais"], "tipo_gestion": r["tipo_gestion"],
                "graduados": r["graduados"], "anio_evaluado": str(r["anio"]),
                "periodo_tipo": conf["period_type"], "periodo_detalle": conf["levels"][r["pais"]]}

    def largest(items: list[dict]) -> list[dict]:
        return sorted(items, key=lambda r: (-r["graduados"], r["institucion"]))[:top]

    national = []
    for country, country_years in sorted(years.items()):
        year_rows = [r for r in universities if r["pais"] == country and r["anio"] == max(country_years)]
        national += [{**common(r), "ranking_nacional": i, "tipo_ranking": conf["ranking_type"],
                      "total_instituciones_pais": len(year_rows), "cobertura": conf["coverage"]}
                     for i, r in enumerate(largest(year_rows), 1)]
    shared = set.intersection(*years.values()) if years else set()
    regional = []
    if shared:
        year_rows = [r for r in universities if r["anio"] == max(shared)]
        regional = [{**common(r), "ranking_regional": i, "criterio_paridad": conf["regional_criterion"]}
                    for i, r in enumerate(largest(year_rows), 1)]
    return national, regional


def _source_ids(session: Session, codes: set[str]) -> dict[str, int]:
    """source_code -> source_id; a configured source not in the database yet is added."""
    found = dict(session.execute(select(Source.source_code, Source.source_id).where(
        Source.source_code.in_(codes))).all())
    for code in codes - set(found):
        conf = sources().get(code)
        if conf is None:
            raise DatasetError(app_config().messages["unknown_source"].format(code=code))
        source = Source(source_code=conf.source_code, name=conf.name, source_kind=conf.kind,
                        base_url=conf.base_url, expected_frequency=conf.expected_frequency)
        session.add(source)
        session.flush()
        found[code] = source.source_id
    return found


def load_universities(session: Session, rows: list[dict], national: list[dict], regional: list[dict],
                      run_id: int | None) -> int:
    """Replace the sources' values, logging what changes or disappears, and rebuild the rankings,
    which derive from those values. Returns the revisions logged."""
    codes = {r["fuente_id"] for r in rows}
    ids = _source_ids(session, codes)
    scope = FactInstitucionesEgresados.fuente_id.in_(codes)
    stored = session.scalars(select(FactInstitucionesEgresados).where(scope)).all()
    revisions = 0
    for code in codes:
        old = {tuple(getattr(o, k) for k in KEY): (o.graduados, None)
               for o in stored if o.fuente_id == code}
        new = {tuple(r[k] for k in KEY): r["graduados"] for r in rows if r["fuente_id"] == code}
        revisions += record_changes(session, DATASET, ids[code], run_id, KEY, old, new, removals=True)
    session.execute(delete(FactInstitucionesEgresados).where(scope))
    session.execute(delete(RankingUniversidadesNacional))
    session.execute(delete(RankingUniversidadesRegional))
    session.flush()
    session.add_all([FactInstitucionesEgresados(**r) for r in rows])
    session.add_all([RankingUniversidadesNacional(**r) for r in national])
    session.add_all([RankingUniversidadesRegional(**r) for r in regional])
    session.flush()
    return revisions


def read_official_files(files: list[OfficialFile], conf: dict) -> tuple[list[dict], list[dict]]:
    by_role: dict[str, list[OfficialFile]] = {}
    for file in files:
        by_role.setdefault(file.role, []).append(file)
    argentina, arg_controls = read_argentina(by_role["arg_latest"][0].path,
                                             by_role["arg_history"][0].path, conf)
    udelar = read_udelar(by_role["udelar"][0].path, conf)
    uruguay, ury_controls = read_uruguay(sorted(by_role["ury"], key=lambda f: f.release), udelar, conf)
    return argentina + read_chile(by_role["chl"][0].path, conf) + uruguay, arg_controls + ury_controls


def _official_links(conf: dict) -> list[tuple[str, int, str, str | None]]:
    """(role, max bytes, url, release) of every file the official pages link now."""
    out = []
    for role, entry in conf["inputs"].items():
        source = profiles()[entry["profile"]] if "profile" in entry else _DirectInput(
            entry["landing_page"], DownloadConf(**entry["download"]))
        out += [(role, source.download.max_bytes, link.url, link.release)
                for link in find_download_links(source)]
    return out


def run_universities_source(session: Session, source_code: str,
                            run: IngestionRun) -> tuple[int, list[str]]:
    """Download, check and load. Returns (rows loaded, warnings); (0, []) if no link changed."""
    conf = analytics_params("universities")
    source = session.scalar(select(Source).where(Source.source_code == source_code))
    links = _official_links(conf)
    last = session.scalars(select(DatasetFile).where(
        DatasetFile.profile_code == conf["dataset_code"], DatasetFile.status == "loaded")).all()
    if last and {d.url for d in last} == {url for _, _, url, _ in links}:
        return 0, []
    datasets_conf = app_config().datasets
    files, datasets = [], []
    for role, max_bytes, url, release in links:
        content = download_sync(url, max_bytes, {"User-Agent": sources().http.user_agent})
        name = Path(urlparse(url).path).name
        path, sha = store_file(content, datasets_conf.path(datasets_conf.raw_dir) / source_code, name)
        dataset = DatasetFile(
            profile_code=conf["dataset_code"], source_id=source.source_id, origin="download",
            file_name=name, url=url, release=release, sha256=sha, size_bytes=len(content),
            stored_path=str(path), status="validated", report={}, created_at=datetime.now(UTC),
            run_id=run.run_id)
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
        raw, controls = read_official_files(files, conf)
    except (KeyError, IndexError, ValueError, StopIteration, TypeError, zipfile.BadZipFile,
            ET.ParseError) as exc:
        raise refuse(f"{type(exc).__name__}: {exc}") from exc
    pending = [c for c in controls if c["resultado"] == conf["control_pending"]]
    if pending:
        first = pending[0]
        raise refuse(f"{len(pending)} controles no coinciden, p. ej. {first['control']} "
                     f"{first['anio']}: {first['valor']} contra {first['esperado']}")
    rows, missing = apply_names(raw, conf)
    national, regional = ranking_rows(rows, conf)
    load_universities(session, rows, national, regional, run.run_id)
    for previous in last:
        previous.status = "replaced"
    for dataset in datasets:
        dataset.status, dataset.loaded_at = "loaded", datetime.now(UTC)
    datasets[0].records = len(rows)
    warnings = [f"Nombres sin normalizar: {', '.join(missing)}"] if missing else []
    return len(rows), warnings
