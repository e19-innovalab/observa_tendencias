"""Find, download, check and load official files (automatic) and uploaded files (manual).

Both paths go through read_dataset (format check) and a revision check against what is already
stored. A file is loaded only if both pass; otherwise nothing changes and the reason is kept in
dataset_files (and, for automatic downloads, in a "format changed" alert).
"""
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.connectors.http import download_sync
from app.core.config_files import analytics_params, app_config, sources
from app.datasets.filecheck import check_file
from app.datasets.profiles import DatasetProfile, normalize_text, profile_for_source
from app.datasets.reader import Issue, ReadReport, read_dataset
from app.ingestion.revisions import OBSERVATION_KEY, record_changes
from app.models import Alert, DatasetFile, Graduate, IngestionRun, Observation, Source
from app.normalization.normalizer import normalize
from app.normalization.periods import to_period_range


class DatasetError(Exception):
    pass


@dataclass
class FoundLink:
    url: str
    release: str | None


def _msg(key: str, **kw) -> str:
    return app_config().datasets.messages[key].format(**kw)


def _page(url: str, profile: DatasetProfile) -> str:
    headers = {"User-Agent": sources().http.user_agent}
    return download_sync(url, profile.download.max_bytes, headers).decode("utf-8", errors="replace")


def _allowed(url: str, profile: DatasetProfile) -> str:
    host = urlparse(url).hostname
    if host not in profile.download.allowed_hosts:
        raise DatasetError(_msg("host_not_allowed", host=host))
    return url


def _latest_link(page_url: str, profile: DatasetProfile, release: str | None = None) -> FoundLink:
    """Latest file link on an official page that matches the profile's pattern."""
    matches = list(re.finditer(profile.download.link_pattern, _page(page_url, profile)))
    if not matches:
        raise DatasetError(_msg("no_link", page=page_url))
    best = max(matches, key=lambda m: m.groupdict().get("release") or m.group(0))
    url = _allowed(urljoin(page_url, best.group(0)), profile)
    found = best.groupdict().get("release")
    if found and len(found) < 4:
        found = profile.download.release_prefix + found
    return FoundLink(url=url, release=found or release)


def find_download_link(profile: DatasetProfile) -> FoundLink:
    return _latest_link(profile.landing_page, profile)


def find_download_links(profile: DatasetProfile) -> list[FoundLink]:
    """Every file to check: one per release page when the profile has page_pattern (one file
    per period), otherwise the latest file on the landing page."""
    conf = profile.download
    if not conf.page_pattern:
        return [find_download_link(profile)]
    pages = {}
    for m in re.finditer(conf.page_pattern, _page(profile.landing_page, profile)):
        release = m.group("release")
        if conf.min_release is None or release >= conf.min_release:
            pages[release] = _allowed(urljoin(profile.landing_page, m.group(0)), profile)
    if not pages:
        raise DatasetError(_msg("no_link", page=profile.landing_page))
    return [_latest_link(url, profile, release) for release, url in sorted(pages.items())]


def store_file(content: bytes, folder: Path, file_name: str) -> tuple[Path, str]:
    """Keep every file: <folder>/<sha256 prefix>_<name>. Returns (path, sha256)."""
    sha = hashlib.sha256(content).hexdigest()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sha[:12]}_{file_name}"
    if not path.exists():
        path.write_bytes(content)
    return path, sha


GRADUATE_KEY = ["career_key", "level", "year"]


def graduate_rows(report: ReadReport) -> dict[tuple, dict]:
    """Aggregated file rows -> one row per (career key, level, year); the field of study kept is
    the one with the most graduates for that career."""
    out: dict[tuple, dict] = {}
    field_weight: dict[tuple, dict[tuple, float]] = {}
    for r in report.rows:
        key = (normalize_text(r["career"]), r["level"], r["year"])
        row = out.setdefault(key, {"career": r["career"], "level": r["level"], "year": r["year"],
                                   "value": 0.0})
        row["value"] += r["value"]
        fields = field_weight.setdefault(key, {})
        f = (r.get("field_area"), r.get("field_subarea"))
        fields[f] = fields.get(f, 0.0) + r["value"]
    for key, row in out.items():
        row["field_area"], row["field_subarea"] = max(field_weight[key].items(),
                                                      key=lambda kv: kv[1])[0]
    return out


def _check_graduate_revisions(session: Session, profile: DatasetProfile, source_id: int,
                              report: ReadReport) -> None:
    limit = profile.expected.max_revision
    if limit is None or not report.rows:
        return
    recent = set(report.periods[-profile.expected.revision_grace_periods:])
    stored = {(g.career_key, g.level, g.year): g.graduates for g in session.scalars(
        select(Graduate).where(Graduate.source_id == source_id)).all()}
    if not stored:
        return
    changed = [f"{year} {career}: {stored[(career, level, year)]} → {row['value']}"
               for (career, level, year), row in graduate_rows(report).items()
               if str(year) not in recent and (career, level, year) in stored
               and stored[(career, level, year)]
               and abs(row["value"] - stored[(career, level, year)])
               / stored[(career, level, year)] > limit]
    if changed:
        report.errors.append(Issue(_msg("revision_too_large", count=len(changed),
                                        max_pct=round(limit * 100, 1), example=changed[0])))


def check_revisions(session: Session, profile: DatasetProfile, source_id: int,
                    report: ReadReport) -> None:
    """Values for periods already published (outside the grace window) must not change more
    than expected.max_revision: a larger change suggests a different series."""
    if profile.target == "graduates":
        _check_graduate_revisions(session, profile, source_id, report)
        return
    limit = profile.expected.max_revision
    if limit is None or not report.records or not report.periods:
        return
    recent = set(report.periods[-profile.expected.revision_grace_periods:]) \
        if profile.expected.revision_grace_periods else set()
    stored = {
        (o.sector_code, o.occupation_code, o.period_start): o.value
        for o in session.scalars(select(Observation).where(
            Observation.source_id == source_id, Observation.data_type == "observed",
            Observation.indicator_code == profile.indicator)).all()
    }
    if not stored:
        return
    from app.normalization.periods import to_period_range

    changed = []
    for r in report.records:
        if r.period in recent:
            continue
        old = stored.get((r.sector_code, r.occupation_code, to_period_range(r.period, r.frequency)[0]))
        if old and abs(r.value - old) / abs(old) > limit:
            changed.append(f"{r.period} {r.sector_code or 'total'}: {old} → {r.value}")
    if changed:
        report.errors.append(Issue(_msg("revision_too_large", count=len(changed),
                                        max_pct=round(limit * 100, 1), example=changed[0])))


def _source(session: Session, code: str) -> Source:
    source = session.scalar(select(Source).where(Source.source_code == code))
    if source is None:
        raise DatasetError(app_config().messages["unknown_source"].format(code=code))
    return source


def validate_file(session: Session, profile: DatasetProfile, path: Path) -> ReadReport:
    report = read_dataset(path, profile)
    if report.ok:
        check_revisions(session, profile, _source(session, profile.source).source_id, report)
    return report


def load_file(session: Session, dataset: DatasetFile, profile: DatasetProfile,
              report: ReadReport, run: IngestionRun) -> int:
    """Write the file's records as observations; the previous loaded file of the same profile
    becomes 'replaced' (for template uploads its values are removed first)."""
    per_period = profile.target_scope == "period"
    previous = session.scalar(select(DatasetFile).where(
        DatasetFile.profile_code == profile.dataset_code, DatasetFile.status == "loaded",
        DatasetFile.dataset_id != dataset.dataset_id,
        *( [DatasetFile.declared_source_name == dataset.declared_source_name]
           if profile.requires_declared_source else [] ),
        *( [DatasetFile.release == dataset.release] if per_period else [] ),
    ).order_by(DatasetFile.loaded_at.desc()))
    replaced: dict[tuple, tuple[float, int | None]] = {}
    if previous is not None:
        if profile.requires_declared_source and previous.run_id:
            from app.ingestion.pipeline import observed_values  # avoid an import cycle

            replaced = observed_values(session, Observation.run_id == previous.run_id)
            session.execute(delete(Observation).where(Observation.run_id == previous.run_id))
        previous.status = "replaced"
        dataset.replaces_dataset_id = previous.dataset_id
    if profile.target == "graduates":
        # the file replaces what this source loaded for the country: the whole series, or only
        # the file's years when each file holds its own period
        scope = [Graduate.source_id == dataset.source_id, Graduate.country_iso3 == profile.country,
                 *( [Graduate.year.in_([int(p) for p in report.periods])] if per_period else [] )]
        rows = graduate_rows(report)
        old = {(g.career_key, g.level, g.year): (g.graduates, g.run_id)
               for g in session.scalars(select(Graduate).where(*scope)).all()}
        record_changes(session, "graduates", dataset.source_id, run.run_id, GRADUATE_KEY, old,
                       {k: r["value"] for k, r in rows.items()}, removals=True)
        session.execute(delete(Graduate).where(*scope))
        session.flush()
        session.add_all([Graduate(
            country_iso3=profile.country, career_key=key[0], career=r["career"], level=r["level"],
            field_area=r["field_area"], field_subarea=r["field_subarea"], year=r["year"],
            graduates=r["value"], source_id=dataset.source_id, run_id=run.run_id,
            dataset_id=dataset.dataset_id) for key, r in rows.items()])
        loaded = len(rows)
    else:
        from app.ingestion.pipeline import upsert_observations  # avoid an import cycle

        result = normalize(report.records, dataset.source_id, run.run_id, datetime.now(UTC))
        upsert_observations(session, result.rows)
        if replaced:  # template uploads: the previous file's values that changed or are gone
            record_changes(session, "observations", dataset.source_id, run.run_id,
                           OBSERVATION_KEY, replaced,
                           {tuple(r[k] for k in OBSERVATION_KEY): r["value"] for r in result.rows},
                           removals=True)
        loaded = len(result.rows)
    dataset.status, dataset.loaded_at, dataset.run_id = "loaded", datetime.now(UTC), run.run_id
    dataset.records = loaded
    return loaded


def _format_alert(session: Session, dataset: DatasetFile, source: Source, report: ReadReport) -> None:
    p = analytics_params("alerts")
    key = f"source_format_changed|{source.source_code}|{dataset.sha256}"
    if session.scalar(select(Alert.alert_id).where(Alert.dedupe_key == key)):
        return
    reason = "; ".join(e.message for e in report.errors[:3])
    session.add(Alert(
        dedupe_key=key, alert_type="source_format_changed",
        severity=p["severities"]["source_format_changed"], entity_type="source",
        source_id=source.source_id, period_label=dataset.release,
        message=p["messages"]["source_format_changed"].format(
            file=dataset.file_name, source=source.name, reason=reason),
        detected_at=datetime.now(UTC),
    ))


def run_dataset_source(session: Session, source_code: str, run: IngestionRun) -> tuple[int, list[str]]:
    """Download, check and load every profile of a dataset source.
    Returns (records loaded, indicator codes that changed)."""
    source = _source(session, source_code)
    conf = app_config().datasets
    loaded, changed = 0, []
    for profile, link in ((p, link) for p in profile_for_source(source_code)
                          for link in find_download_links(p)):
        per_period = profile.target_scope == "period"
        last = session.scalar(select(DatasetFile).where(
            DatasetFile.profile_code == profile.dataset_code, DatasetFile.status == "loaded",
            *( [DatasetFile.release == link.release] if per_period else [] ),
        ).order_by(DatasetFile.loaded_at.desc()))
        if last is not None and last.url == link.url and not profile.download.always_download:
            continue  # same release still linked on the official page: nothing to download
        content = download_sync(link.url, profile.download.max_bytes,
                                {"User-Agent": sources().http.user_agent})
        file_name = Path(urlparse(link.url).path).name
        path, sha = store_file(content, conf.path(conf.raw_dir) / source_code, file_name)
        dataset = DatasetFile(
            profile_code=profile.dataset_code, source_id=source.source_id, origin="download",
            file_name=file_name, url=link.url, release=link.release, sha256=sha,
            size_bytes=len(content), stored_path=str(path), status="validated", report={},
            created_at=datetime.now(UTC), run_id=run.run_id,
        )
        session.add(dataset)
        if last is not None and last.sha256 == sha:
            dataset.status = "unchanged"
            dataset.report = {"ok": True, "unchanged_from": last.dataset_id}
            continue
        report = validate_file(session, profile, path)
        if per_period and link.release and report.ok and report.periods != [link.release]:
            report.errors.append(Issue(_msg("outline_release_differs", release=link.release,
                                            found=", ".join(report.periods))))
        dataset.report = report.summary()
        session.flush()
        if not report.ok:
            dataset.status = "format_changed"
            _format_alert(session, dataset, source, report)
            raise DatasetError(f"{profile.dataset_code}: " + "; ".join(
                e.message for e in report.errors[:3]))
        loaded += load_file(session, dataset, profile, report, run)
        if profile.indicator:
            changed.append(profile.indicator)
    return loaded, changed


def official_overlaps(session: Session, source_id: int, report: ReadReport) -> dict | None:
    """Values of the file that already exist from another (official) source: same indicator,
    country, sector, occupation, period and frequency. None when there are none."""
    keys = {}
    for r in report.records:
        start, _ = to_period_range(r.period, r.frequency)
        keys[(r.indicator_code, r.country_iso3, r.sector_code, r.occupation_code, start, r.frequency)] = r
    if not keys:
        return None
    rows = session.execute(
        select(Observation.indicator_code, Observation.country_iso3, Observation.sector_code,
               Observation.occupation_code, Observation.period_start, Observation.frequency,
               Observation.value, Source.name)
        .join(Source, Source.source_id == Observation.source_id)
        .where(Observation.source_id != source_id, Observation.data_type == "observed",
               Observation.indicator_code.in_({k[0] for k in keys}),
               Observation.country_iso3.in_({k[1] for k in keys}),
               Observation.period_start.in_({k[4] for k in keys}))).all()
    found = [(row, keys[tuple(row[:6])]) for row in rows if tuple(row[:6]) in keys]
    if not found:
        return None
    conf = app_config().datasets
    by_source: dict[str, int] = {}
    for row, _ in found:
        by_source[row.name] = by_source.get(row.name, 0) + 1
    examples = [_msg("overlap_example", indicator=rec.indicator_code, country=rec.country_iso3,
                     period=rec.period, official=row.value, uploaded=rec.value)
                for row, rec in found[:conf.overlap_examples]]
    count = len({tuple(row[:6]) for row, _ in found})
    return {"count": count, "by_source": by_source, "examples": examples,
            "message": _msg("overlap_official", count=count,
                            sources=", ".join(f"{k}: {v}" for k, v in by_source.items()),
                            examples="; ".join(examples))}


def register_upload(session: Session, profile: DatasetProfile, content: bytes, file_name: str,
                    declared_name: str | None, declared_url: str | None,
                    reference_date: date | None) -> tuple[DatasetFile, ReadReport]:
    """Store an uploaded file and its validation report (status validated or rejected)."""
    conf = app_config().datasets
    source = _source(session, profile.source)
    path, sha = store_file(content, conf.path(conf.uploads_dir) / profile.dataset_code, file_name)
    dataset = DatasetFile(
        profile_code=profile.dataset_code, source_id=source.source_id, origin="upload",
        file_name=file_name, sha256=sha, size_bytes=len(content), stored_path=str(path),
        status="validated", report={}, declared_source_name=declared_name,
        declared_source_url=declared_url, reference_date=reference_date,
        created_at=datetime.now(UTC),
    )
    problems = check_file(content, file_name, profile)
    if problems:  # not what it says it is: not read at all (kept, with the reason, in the history)
        report = ReadReport(errors=[Issue(m) for m in problems])
    else:
        report = validate_file(session, profile, path)
        if report.ok and profile.is_long:
            report.overlaps = official_overlaps(session, source.source_id, report)
            if report.overlaps:
                report.warnings.append(Issue(report.overlaps["message"], kind="overlap"))
    if profile.requires_declared_source and not (declared_name and declared_url):
        report.errors.insert(0, Issue(_msg("declared_source_required")))
    dataset.report = report.summary()
    dataset.records = len(report.records)
    dataset.status = "validated" if report.ok else "rejected"
    session.add(dataset)
    session.flush()
    return dataset, report
