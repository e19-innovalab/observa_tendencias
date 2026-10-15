from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models import JobPosting
from app.schemas.analytics import JobItem, JobsPage, JobsSummary, JobsSummaryCell

router = APIRouter(tags=["jobs"])


def _filters(pais: str | None, provincia: str | None, sector: str | None, q: str | None):
    conds = []
    if pais:
        conds.append(JobPosting.pais == pais.upper())
    if provincia:
        conds.append(JobPosting.provincia == provincia)
    if sector:
        conds.append(JobPosting.sector == sector)
    if q:
        conds.append(JobPosting.titulo.ilike(f"%{q}%"))
    return conds


@router.get("/jobs", response_model=JobsPage)
def list_jobs(
    pais: str | None = None,
    provincia: str | None = None,
    sector: str | None = None,
    q: str | None = Query(None, description="Texto a buscar en el título"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    conds = _filters(pais, provincia, sector, q)
    total = session.scalar(select(func.count()).select_from(JobPosting).where(*conds))
    rows = session.scalars(
        select(JobPosting).where(*conds)
        .order_by(JobPosting.fecha_publicacion.desc(), JobPosting.id)
        .limit(limit).offset(offset)
    ).all()
    return JobsPage(
        total=total, limit=limit, offset=offset,
        items=[JobItem.model_validate(r) for r in rows],
    )


@router.get("/jobs/summary", response_model=JobsSummary)
def jobs_summary(pais: str | None = None, session: Session = Depends(get_session)):
    conds = _filters(pais, None, None, None)
    cells = session.execute(
        select(JobPosting.provincia, JobPosting.sector, func.count())
        .where(*conds).group_by(JobPosting.provincia, JobPosting.sector)
        .order_by(JobPosting.provincia, JobPosting.sector)
    ).all()
    last = session.scalar(select(func.max(JobPosting.scraped_at)).where(*conds))
    return JobsSummary(
        total=sum(n for _, _, n in cells),
        scraped_at=last,
        por_provincia_sector=[JobsSummaryCell(provincia=p, sector=s, n=n) for p, s, n in cells],
    )
