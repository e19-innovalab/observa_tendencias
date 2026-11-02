"""Ingestion pipeline: fetch -> canonical records -> normalize -> upsert observations.

Every run is recorded in ingestion_runs (the update history shown to users). After new data is
saved, trends and projections of the affected indicators are recalculated.
"""
import asyncio
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from app.analytics.recompute import (
    recompute,
    refresh_ludita,
    refresh_moctezuma,
    refresh_red_queen,
    refresh_skill_gaps,
)
from app.connectors.registry import build_connector
from app.core.config_files import app_config, indicators, sources
from app.datasets.ingest import DatasetError, run_dataset_source
from app.ingestion.revisions import OBSERVATION_KEY, record_changes
from app.models import EducationMismatchCell, IngestionRun, Observation, Source
from app.normalization.normalizer import normalize
from app.skills.esco import run_esco_source

MAX_ERROR_LENGTH = 2000
CELL_KEY = ["country_iso3", "year", "isco_group", "band"]


class IngestionError(Exception):
    pass


OBSERVED = "observed"


def observed_values(session: Session, *conds) -> dict[tuple, tuple[float, int | None]]:
    """{OBSERVATION_KEY values: (value, run_id)} of the observed rows matching conds."""
    cols = [getattr(Observation, k) for k in OBSERVATION_KEY]
    return {tuple(r[:-2]): (r[-2], r[-1]) for r in session.execute(
        select(*cols, Observation.value, Observation.run_id)
        .where(Observation.data_type == OBSERVED, *conds)).all()}


def upsert_observations(session: Session, rows: list[dict]) -> None:
    """Idempotent write keyed by OBSERVATION_KEY. Postgres relies on the NULLS NOT DISTINCT
    unique constraint; SQLite (tests) treats NULLs as distinct, so it replaces row by row.
    Observed values that change are kept in data_revisions first."""
    if not rows:
        return
    observed = [r for r in rows if r["data_type"] == OBSERVED]
    for indicator, source_id in {(r["indicator_code"], r["source_id"]) for r in observed}:
        old = observed_values(session, Observation.indicator_code == indicator,
                              Observation.source_id == source_id)
        if old:
            record_changes(session, "observations", source_id, observed[0]["run_id"],
                           OBSERVATION_KEY, old,
                           {tuple(r[k] for k in OBSERVATION_KEY): r["value"] for r in observed
                            if r["indicator_code"] == indicator and r["source_id"] == source_id},
                           removals=False)
    _write_observations(session, rows)


def _write_observations(session: Session, rows: list[dict]) -> None:
    if session.get_bind().dialect.name == "postgresql":
        stmt = postgresql.insert(Observation)
        update = {k: stmt.excluded[k] for k in rows[0] if k not in OBSERVATION_KEY}
        session.execute(
            stmt.on_conflict_do_update(constraint="uq_observations_key", set_=update), rows
        )
        return
    for row in rows:
        session.execute(delete(Observation).where(
            *(getattr(Observation, k).is_not_distinct_from(row[k]) for k in OBSERVATION_KEY)
        ))
    session.execute(sqlite.insert(Observation), rows)


DATASET_CONNECTOR = "dataset_download"
ESCO_CONNECTOR = "esco"
SKILL_VERSIONS_CONNECTOR = "skill_versions"


def prune_out_of_scope(session: Session, source_id: int, specs) -> None:
    """A series restricted to some countries (indicators.yaml -> countries) owns that breakdown
    only for them: rows this source stored earlier for other countries are removed, so two
    sources never mix in one series (e.g. Chile by occupation: SIMEL, not ILOSTAT)."""
    for indicator, series in specs:
        if not series.countries:
            continue
        conds = [Observation.source_id == source_id, Observation.indicator_code == indicator.code,
                 Observation.data_type == "observed",
                 Observation.country_iso3.not_in(series.countries)]
        if series.occupation_dimension:
            conds.append(Observation.occupation_code.is_not(None))
        elif series.sector_dimension:
            conds.append(Observation.sector_code.is_not(None))
        else:
            conds += [Observation.occupation_code.is_(None), Observation.sector_code.is_(None)]
        removed = observed_values(session, *conds)
        if removed:
            record_changes(session, "observations", source_id, None, OBSERVATION_KEY, removed,
                           {}, removals=True)
        session.execute(delete(Observation).where(*conds))


def replace_education_cells(session: Session, source_id: int, run_id: int,
                            cells: list[dict]) -> None:
    """The source's cells are replaced as a whole: every mismatch series of a source fetches the
    same table, so duplicates are dropped by key."""
    now = datetime.now(UTC)
    unique = {(c["country_iso3"], c["year"], c["isco_group"], c["band"]): c for c in cells}
    old = {(c.country_iso3, c.year, c.isco_group, c.band): (c.employed, c.run_id)
           for c in session.scalars(select(EducationMismatchCell).where(
               EducationMismatchCell.source_id == source_id)).all()}
    record_changes(session, "education_mismatch_cells", source_id, run_id, CELL_KEY, old,
                   {k: c["employed"] for k, c in unique.items()}, removals=True)
    session.execute(delete(EducationMismatchCell).where(
        EducationMismatchCell.source_id == source_id))
    session.add_all(EducationMismatchCell(**c, source_id=source_id, run_id=run_id, fetched_at=now)
                    for c in unique.values())


def _finish(session: Session, run: IngestionRun, changed: list[str], issues: list[str]) -> None:
    try:  # derived results must not undo a successful fetch
        recompute(session, changed)
    except Exception as exc:
        session.rollback()
        issues.append(f"recálculo fallido: {type(exc).__name__}: {exc}")
    run.status = "success" if not issues else "partial"
    run.error_message = "; ".join(issues)[:MAX_ERROR_LENGTH] or None


def run_source(
    session: Session, source_code: str, triggered_by: str, since_year: int | None = None
) -> IngestionRun:
    messages = app_config().messages
    source_conf = sources().get(source_code)
    if source_conf is None:
        raise IngestionError(messages["unknown_source"].format(code=source_code))
    is_dataset = source_conf.connector == DATASET_CONNECTOR
    is_esco = source_conf.connector == ESCO_CONNECTOR
    is_versions = source_conf.connector == SKILL_VERSIONS_CONNECTOR
    special = is_dataset or is_esco or is_versions
    connector = None if special else build_connector(source_conf)
    if connector is None and not special:
        raise IngestionError(messages["source_without_connector"].format(code=source_code))
    source = session.scalar(select(Source).where(Source.source_code == source_code))
    if source is None:
        raise IngestionError(messages["unknown_source"].format(code=source_code))

    run = IngestionRun(source_id=source.source_id, started_at=datetime.now(UTC),
                       status="running", triggered_by=triggered_by)
    session.add(run)
    session.commit()

    try:
        if is_versions:
            # skill profiles per release (Reina Roja): only releases not stored yet are fetched
            from app.skills.versions import run_skill_versions  # heavy imports, only when used

            releases, profiles, skipped = run_skill_versions(session, source_code)
            if releases:
                refresh_red_queen(session)
            session.commit()
            run.records_fetched, run.records_normalized = releases, profiles
            run.status = "partial" if skipped else "success"
            run.error_message = (f"ocupaciones ESCO omitidas (error del servidor): {skipped}"
                                 if skipped else None)
        elif is_esco:
            # reference data (skills by occupation): no observations, no recalculation
            groups, rows, skipped = run_esco_source(session, source_code)
            session.commit()
            refresh_skill_gaps(session)
            session.commit()
            run.records_fetched, run.records_normalized = groups, rows
            run.status = "partial" if skipped else "success"
            run.error_message = (f"ocupaciones ESCO omitidas (error del servidor): "
                                 f"{', '.join(skipped)}"[:MAX_ERROR_LENGTH] if skipped else None)
        elif is_dataset:
            # official files: download, check the validated format, load only if it matches
            loaded, changed = run_dataset_source(session, source_code, run)
            session.commit()
            run.records_fetched = run.records_normalized = loaded
            if loaded and not changed:  # files without indicators (e.g. graduates)
                refresh_skill_gaps(session)
                refresh_moctezuma(session)
                refresh_ludita(session)
                session.commit()
            _finish(session, run, changed, [])
        else:
            specs = indicators().series_for(source_code)
            payloads = asyncio.run(connector.fetch(specs, since_year))
            records = [rec for p in payloads for rec in connector.to_canonical(p)]
            result = normalize(records, source.source_id, run.run_id, datetime.now(UTC))
            prune_out_of_scope(session, source.source_id, specs)
            upsert_observations(session, result.rows)
            cells = [c for p in payloads for c in connector.education_cells(p)]
            if cells:
                replace_education_cells(session, source.source_id, run.run_id, cells)
            session.commit()
            run.records_fetched = len(records)
            run.records_normalized = len(result.rows)
            _finish(session, run, sorted({r["indicator_code"] for r in result.rows}),
                    sorted(set(result.issues)))
    except DatasetError as exc:
        # the file record and its alert are kept; nothing was loaded from the bad file
        session.commit()
        run.status = "format_changed"
        run.error_message = str(exc)[:MAX_ERROR_LENGTH]
    except Exception as exc:  # the run must be recorded as failed whatever went wrong
        session.rollback()
        run.status = "failed"
        run.error_message = f"{type(exc).__name__}: {exc}"[:MAX_ERROR_LENGTH]
    run.finished_at = datetime.now(UTC)
    session.add(run)
    session.commit()
    return run
