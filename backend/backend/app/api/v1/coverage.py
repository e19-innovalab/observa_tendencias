from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models import CoverageReport
from app.schemas.analytics import CoverageItem

router = APIRouter(tags=["coverage"])


@router.get("/coverage", response_model=list[CoverageItem])
def coverage(
    country: str | None = Query(None, description="ISO3 (ARG, URY, CHL)"),
    pais: str | None = Query(None, description="Igual que country (se mantiene por compatibilidad)"),
    session: Session = Depends(get_session),
):
    stmt = select(CoverageReport).order_by(CoverageReport.pais, CoverageReport.sector)
    if country or pais:
        stmt = stmt.where(CoverageReport.pais == (country or pais).upper())
    return session.scalars(stmt).all()
