from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models import Country, Occupation, Sector
from app.schemas.observatory import CountryItem, OccupationItem, SectorItem

router = APIRouter(tags=["catalog"])


@router.get("/countries", response_model=list[CountryItem])
def countries(session: Session = Depends(get_session)):
    return session.scalars(select(Country).order_by(Country.name_es)).all()


@router.get("/sectors", response_model=list[SectorItem])
def sectors(session: Session = Depends(get_session)):
    return session.scalars(select(Sector).order_by(Sector.name)).all()


@router.get("/occupations", response_model=list[OccupationItem])
def occupations(
    sector: str | None = None,
    featured: bool | None = Query(None, description="true: solo las destacadas del catálogo"),
    q: str | None = Query(None, description="Texto a buscar en el nombre o el código CIUO"),
    session: Session = Depends(get_session),
):
    stmt = select(Occupation).order_by(Occupation.name)
    if sector:
        stmt = stmt.where(Occupation.sector_code == sector)
    if featured is not None:
        stmt = stmt.where(Occupation.is_featured.is_(featured))
    if q:
        stmt = stmt.where(or_(Occupation.name.ilike(f"%{q}%"), Occupation.name_en.ilike(f"%{q}%"),
                              Occupation.occupation_code.startswith(q)))
    return session.scalars(stmt).all()
