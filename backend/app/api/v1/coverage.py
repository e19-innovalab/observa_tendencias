from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models import CoverageReport
from app.schemas.analytics import CoverageItem

router = APIRouter(tags=["coverage"])


@router.get("/coverage", response_model=list[CoverageItem])
def coverage(pais: str | None = None, session: Session = Depends(get_session)):
    stmt = select(CoverageReport).order_by(CoverageReport.pais, CoverageReport.sector)
    if pais:
        stmt = stmt.where(CoverageReport.pais == pais.upper())
    return session.scalars(stmt).all()
