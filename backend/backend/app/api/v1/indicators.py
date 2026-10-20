from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config_files import IndicatorConf, app_config, catalog, indicators
from app.core.database import get_session
from app.schemas.observatory import (
    ComparePoint,
    CompareResult,
    DashboardSummary,
    HighlightCard,
    IndicatorItem,
    ObservationsPage,
)
from app.services.observations import (
    change_kind_for,
    compute_change,
    indicator_item,
    latest_pair,
    query_points,
    source_refs,
)

router = APIRouter(tags=["indicators"])
_pagination = app_config().pagination
ChangeKind = Literal["absolute", "relative"]
DataType = Literal["observed", "calculated", "projected"]


def _indicator(code: str) -> IndicatorConf:
    ind = indicators().get(code)
    if ind is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            app_config().messages["unknown_indicator"].format(code=code))
    return ind


def _country_list(countries: str | None) -> list[str]:
    if countries:
        return [c.strip().upper() for c in countries.split(",") if c.strip()]
    return [c.iso3 for c in catalog().countries]


@router.get("/indicators", response_model=list[IndicatorItem])
def list_indicators(domain: str | None = None, session: Session = Depends(get_session)):
    refs = source_refs(session)
    return [indicator_item(i, refs) for i in indicators().indicators
            if domain is None or i.domain == domain]


@router.get("/observations", response_model=ObservationsPage)
def observations(
    indicator: str,
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    sector: str | None = None,
    occupation: str | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    data_type: DataType | None = None,
    limit: int = Query(_pagination.observations_max_limit, ge=1,
                       le=_pagination.observations_max_limit),
    session: Session = Depends(get_session),
):
    ind = _indicator(indicator)
    points = query_points(session, ind, _country_list(country), sector, occupation,
                          from_year, to_year, data_type)
    return ObservationsPage(indicator=indicator_item(ind, source_refs(session)),
                            total=len(points), items=points[:limit])


@router.get("/compare", response_model=CompareResult)
def compare(
    indicator: str,
    countries: str | None = Query(None, description="ISO3 separados por coma (default: catálogo)"),
    sector: str | None = None,
    occupation: str | None = None,
    change: ChangeKind | None = None,
    session: Session = Depends(get_session),
):
    """Latest observed value per country vs. the previous period (bar chart in Panorama)."""
    ind = _indicator(indicator)
    kind = change_kind_for(ind.unit, change)
    items = []
    for iso3 in _country_list(countries):
        cur, prev = latest_pair(query_points(session, ind, [iso3], sector, occupation))
        items.append(ComparePoint(country_iso3=iso3, current=cur, previous=prev,
                                  change=compute_change(cur, prev, kind), change_kind=kind))
    return CompareResult(indicator=indicator_item(ind, source_refs(session)),
                         sector_code=sector, items=items)


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(country: str, session: Session = Depends(get_session)):
    """Cards of the Inicio screen; which indicators appear is set in config/app.yaml."""
    refs = source_refs(session)
    cards = []
    for h in app_config().dashboard.highlights:
        ind = _indicator(h.indicator)
        cur, prev = latest_pair(query_points(session, ind, [country]))
        cards.append(HighlightCard(indicator=indicator_item(ind, refs), country_iso3=country.upper(),
                                   current=cur, previous=prev,
                                   change=compute_change(cur, prev, h.change), change_kind=h.change))
    return DashboardSummary(country_iso3=country.upper(), highlights=cards)
