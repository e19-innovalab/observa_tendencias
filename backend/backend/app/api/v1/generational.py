from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.indicators import _country_list
from app.core.config_files import app_config, catalog, indicators
from app.core.database import get_session
from app.models import Observation
from app.schemas.observatory import GapCountry, GapPoint, GenerationalGap
from app.services.observations import indicator_item, source_refs

router = APIRouter(tags=["generational_gap"])


def _national(session: Session, code: str, countries: list[str]) -> dict[str, dict[int, float]]:
    """{country: {year: value}} of an annual national series (no sector, no occupation)."""
    rows = session.execute(select(Observation.country_iso3, Observation.period_start,
                                  Observation.value).where(
        Observation.indicator_code == code, Observation.country_iso3.in_(countries),
        Observation.data_type == "observed", Observation.frequency == "A",
        Observation.sector_code.is_(None), Observation.occupation_code.is_(None))).all()
    out: dict[str, dict[int, float]] = {}
    for country, start, value in rows:
        out.setdefault(country, {})[start.year] = value
    return out


@router.get("/generational-gap", response_model=GenerationalGap)
def generational_gap(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    session: Session = Depends(get_session),
):
    """Youth unemployment (15-24) over total unemployment per country and year, both from the
    same survey series (app.yaml -> generational_gap), with a headline for the latest year."""
    conf = app_config().generational_gap
    countries = _country_list(country)
    youth = _national(session, conf.youth_indicator, countries)
    total = _national(session, conf.total_indicator, countries)
    names = {c.iso3: c.name_es for c in catalog().countries}
    refs = source_refs(session)
    out = []
    for iso3 in countries:
        points = [GapPoint(year=y, youth=youth[iso3][y], total=total[iso3][y],
                           ratio=youth[iso3][y] / total[iso3][y])
                  for y in sorted(set(youth.get(iso3, {})) & set(total.get(iso3, {})))
                  if total[iso3][y]]
        latest = points[-1] if points else None
        headline = conf.headline.format(
            country=names.get(iso3, iso3), year=latest.year,
            ratio=f"{latest.ratio:.1f}".replace(".", ",")) if latest else None
        out.append(GapCountry(country_iso3=iso3, points=points, latest=latest, headline=headline))
    youth_item = indicator_item(indicators().get(conf.youth_indicator), refs)
    return GenerationalGap(
        title=conf.title, description=conf.description, youth=youth_item,
        total=indicator_item(indicators().get(conf.total_indicator), refs),
        source=youth_item.sources[0].name if youth_item.sources else None, countries=out)
