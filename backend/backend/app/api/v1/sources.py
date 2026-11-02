from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_permission
from app.core.config_files import analytics_params, app_config, sources
from app.core.database import get_session
from app.ingestion.pipeline import IngestionError, run_source
from app.models import DataRevision, IngestionRun, Source
from app.schemas.observatory import RevisionItem, RunItem, SourceItem

router = APIRouter(prefix="/sources", tags=["sources"])
_pagination = app_config().pagination
SUCCESS_STATUSES = ("success", "partial")


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=UTC) if dt is not None and dt.tzinfo is None else dt


def _status(expected_frequency: str | None, last_run: IngestionRun | None,
            last_success: IngestionRun | None) -> str:
    labels = app_config().source_status
    if last_run is None:
        return labels["never_run"]
    if last_run.status == "failed":
        return labels["unavailable"]
    days = sources().frequency_days.get(expected_frequency or "")
    finished = _aware(last_success.finished_at) if last_success else None
    if days and finished:
        limit = timedelta(days=days * analytics_params("alerts")["stale_factor"])
        if datetime.now(UTC) - finished > limit:
            return labels["stale"]
    return labels["ok"]


def _item(session: Session, source: Source) -> SourceItem:
    runs = select(IngestionRun).where(IngestionRun.source_id == source.source_id)
    last_run = session.scalar(runs.order_by(IngestionRun.started_at.desc()))
    last_success = session.scalar(
        runs.where(IngestionRun.status.in_(SUCCESS_STATUSES))
        .order_by(IngestionRun.finished_at.desc())
    )
    conf = sources().get(source.source_code)
    return SourceItem(
        code=source.source_code, name=source.name, kind=source.source_kind,
        base_url=source.base_url, expected_frequency=source.expected_frequency,
        has_connector=bool(conf and conf.connector),
        status=_status(source.expected_frequency, last_run, last_success),
        last_success_at=last_success.finished_at if last_success else None,
        last_run=RunItem.model_validate(last_run) if last_run else None,
    )


def _source(session: Session, code: str) -> Source:
    source = session.scalar(select(Source).where(Source.source_code == code))
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            app_config().messages["unknown_source"].format(code=code))
    return source


@router.get("", response_model=list[SourceItem])
def list_sources(session: Session = Depends(get_session)):
    rows = session.scalars(select(Source).order_by(Source.source_code)).all()
    return [_item(session, s) for s in rows]


@router.get("/{code}/runs", response_model=list[RunItem])
def source_runs(
    code: str,
    limit: int = Query(_pagination.default_limit, ge=1, le=_pagination.max_limit),
    session: Session = Depends(get_session),
):
    source = _source(session, code)
    return session.scalars(
        select(IngestionRun).where(IngestionRun.source_id == source.source_id)
        .order_by(IngestionRun.started_at.desc()).limit(limit)
    ).all()


@router.get("/{code}/revisions", response_model=list[RevisionItem])
def source_revisions(
    code: str,
    dataset: str | None = Query(None, description="observations, graduates o education_mismatch_cells"),
    run_id: int | None = Query(None, description="Solo los cambios de esa ejecución"),
    limit: int = Query(_pagination.default_limit, ge=1, le=_pagination.max_limit),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """History of the source's data: every value a later load changed or removed, newest
    first, with the value published before."""
    source = _source(session, code)
    stmt = select(DataRevision).where(DataRevision.source_id == source.source_id)
    if dataset:
        stmt = stmt.where(DataRevision.dataset == dataset)
    if run_id is not None:
        stmt = stmt.where(DataRevision.run_id == run_id)
    return session.scalars(stmt.order_by(DataRevision.revised_at.desc(),
                                         DataRevision.revision_id.desc())
                           .offset(offset).limit(limit)).all()


@router.post("/{code}/refresh", response_model=RunItem, dependencies=[Depends(require_permission("manage_data"))])
def refresh_source(code: str, since_year: int | None = None,
                   session: Session = Depends(get_session)):
    _source(session, code)
    try:
        return run_source(session, code, "manual", since_year)
    except IngestionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
