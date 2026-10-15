from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models import GraduateProjection, GraduateTrend
from app.schemas.analytics import GraduateProjectionItem, GraduateTrendItem, GraduateTrends

router = APIRouter(prefix="/graduates", tags=["graduates"])


@router.get("/trends", response_model=GraduateTrends)
def graduate_trends(
    pais: str | None = None,
    tendencia: str | None = None,
    session: Session = Depends(get_session),
):
    stmt = select(GraduateTrend).order_by(GraduateTrend.pais, GraduateTrend.nombre)
    if pais:
        stmt = stmt.where(GraduateTrend.pais == pais.lower())
    if tendencia:
        stmt = stmt.where(GraduateTrend.tendencia == tendencia)
    return GraduateTrends(
        items=[GraduateTrendItem.model_validate(r) for r in session.scalars(stmt).all()]
    )


@router.get("/projections", response_model=list[GraduateProjectionItem])
def graduate_projections(
    pais: str | None = None,
    nombre: str | None = None,
    session: Session = Depends(get_session),
):
    stmt = select(GraduateProjection).order_by(
        GraduateProjection.pais, GraduateProjection.nombre, GraduateProjection.anio
    )
    if pais:
        stmt = stmt.where(GraduateProjection.pais == pais.lower())
    if nombre:
        stmt = stmt.where(GraduateProjection.nombre == nombre)
    return session.scalars(stmt).all()
