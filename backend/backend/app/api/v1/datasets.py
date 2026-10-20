from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.recompute import recompute
from app.core.config_files import app_config
from app.core.database import get_session
from app.core.security import require_api_key
from app.datasets.ingest import load_file, register_upload, validate_file
from app.datasets.profiles import profiles
from app.models import DatasetFile, IngestionRun
from app.schemas.observatory import DatasetFileItem, DatasetProfileItem, DatasetUploadResult

router = APIRouter(prefix="/datasets", tags=["datasets"])
_pagination = app_config().pagination
ALLOWED_SUFFIXES = (".xlsx", ".csv")


def _profile(code: str):
    profile = profiles().get(code)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            app_config().messages["unknown_profile"].format(code=code))
    return profile


@router.get("/profiles", response_model=list[DatasetProfileItem])
def list_profiles():
    """Files the platform knows how to read: what to upload and which format is expected."""
    return [DatasetProfileItem(
        dataset_code=p.dataset_code, title=p.title, source=p.source, landing_page=p.landing_page,
        automatic=p.download is not None, requires_declared_source=p.requires_declared_source,
        file_format=p.file.format, sheet=p.file.sheet, expected_headers=p.expected.headers,
        template_columns=p.long_format.columns if p.long_format else None,
        required_columns=[p.long_format.columns[k] for k in p.long_format.required]
        if p.long_format else None,
        mapped_columns={k: v.model_dump(exclude_defaults=True) for k, v in p.columns.items()}
        or None,
    ) for p in profiles().values()]


@router.get("", response_model=list[DatasetFileItem])
def list_files(
    profile: str | None = None,
    origin: str | None = Query(None, description="download | upload"),
    limit: int = Query(_pagination.default_limit, ge=1, le=_pagination.max_limit),
    session: Session = Depends(get_session),
):
    """History of every official file read (downloaded or uploaded) and what happened to it."""
    stmt = select(DatasetFile).order_by(DatasetFile.created_at.desc()).limit(limit)
    if profile:
        stmt = stmt.where(DatasetFile.profile_code == profile)
    if origin:
        stmt = stmt.where(DatasetFile.origin == origin)
    return session.scalars(stmt).all()


@router.get("/{dataset_id}", response_model=DatasetFileItem)
def get_file(dataset_id: int, session: Session = Depends(get_session)):
    dataset = session.get(DatasetFile, dataset_id)
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            app_config().messages["unknown_dataset"].format(id=dataset_id))
    return dataset


@router.post("/upload", response_model=DatasetUploadResult,
             dependencies=[Depends(require_api_key)])
async def upload(
    file: UploadFile = File(...),
    profile: str = Form(..., description="dataset_code de /datasets/profiles"),
    declared_source_name: str | None = Form(None),
    declared_source_url: str | None = Form(None),
    reference_date: date | None = Form(None),
    session: Session = Depends(get_session),
):
    """Step 1: store the file and check it. Nothing is loaded until /{id}/commit."""
    conf = app_config().datasets
    prof = _profile(profile)
    name = Path(file.filename or "archivo").name
    if Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            conf.messages["unsupported_format"].format(name=name))
    content = await file.read(conf.max_upload_bytes + 1)
    if len(content) > conf.max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, conf.messages[
            "too_large"].format(max_mb=round(conf.max_upload_bytes / 1e6)))
    dataset, report = register_upload(session, prof, content, name, declared_source_name,
                                      declared_source_url, reference_date)
    session.commit()
    preview = [r.model_dump() for r in report.records[:conf.preview_rows]] if report.ok else []
    return DatasetUploadResult(**DatasetFileItem.model_validate(dataset).model_dump(),
                               preview=preview)


@router.post("/{dataset_id}/commit", response_model=DatasetFileItem,
             dependencies=[Depends(require_api_key)])
def commit(dataset_id: int, session: Session = Depends(get_session)):
    """Step 2: load a validated upload. A previous load of the same profile (and declared source)
    is replaced. Trends, projections, the index and alerts are recalculated."""
    dataset = get_file(dataset_id, session)
    messages = app_config().messages
    if dataset.status != "validated":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            messages["dataset_not_committable"].format(status=dataset.status))
    prof = _profile(dataset.profile_code)
    report = validate_file(session, prof, Path(dataset.stored_path))  # data may have changed since
    if not report.ok:
        dataset.status, dataset.report = "rejected", report.summary()
        session.commit()
        raise HTTPException(status.HTTP_409_CONFLICT,
                            messages["dataset_not_committable"].format(status="rejected"))
    run = IngestionRun(source_id=dataset.source_id, started_at=datetime.now(UTC),
                       status="running", triggered_by="upload")
    session.add(run)
    session.flush()
    loaded = load_file(session, dataset, prof, report, run)
    run.records_fetched = run.records_normalized = loaded
    session.commit()
    recompute(session, sorted({r.indicator_code for r in report.records}))
    run.status, run.finished_at = "success", datetime.now(UTC)
    session.commit()
    return dataset
