from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.employability import level_for
from app.analytics.employability_run import NOT_APPLICABLE
from app.analytics.moctezuma import SIDES
from app.analytics.recompute import params_digest
from app.api.v1.employability import View, _occupation, _ref, _sector_name
from app.api.v1.indicators import _country_list
from app.core.config_files import analytics_params, app_config, catalog
from app.core.config_files import moctezuma_history as historical_config
from app.core.database import get_session
from app.models import Methodology, MoctezumaScore
from app.schemas.observatory import (
    LuditaSource,
    MoctezumaAlternativePoint,
    MoctezumaComponent,
    MoctezumaCountry,
    MoctezumaCountryPoint,
    MoctezumaDimension,
    MoctezumaEvent,
    MoctezumaHistoricalPoint,
    MoctezumaHistory,
    MoctezumaHistoryPoint,
    MoctezumaItem,
    MoctezumaPage,
    MoctezumaRange,
    MoctezumaReference,
    MoctezumaSide,
    OccupationItem,
)

router = APIRouter(tags=["moctezuma"])
_pagination = app_config().pagination


def _current_method(session: Session) -> Methodology | None:
    """Scores shown are those of the parameter set currently in config/analytics.yaml."""
    digest = params_digest("moctezuma_index")[2]
    return session.scalar(select(Methodology).where(
        Methodology.methodology_type == "moctezuma_index", Methodology.params_hash == digest))


def _sides(section: str = "moctezuma") -> list[MoctezumaSide]:
    """The two sides of a two-sided index (Moctezuma: Ritmo del cambio and Capacidad de
    respuesta): definitions and the dimensions behind them."""
    p = analytics_params(section)
    labels = getattr(app_config(), section)
    out = []
    for side in p.get("sides", SIDES):
        dims = []
        for dim, c in p["dimensions"].items():
            if c["side"] != side:
                continue
            info = labels.dimension_info.get(dim)
            dims.append(MoctezumaDimension(
                dimension=dim, label=labels.dimensions.get(dim, dim), weight=c["weight"],
                higher_is_more=c["higher_is_more"], indicator=c["indicator"], scope=c["scope"],
                definition=info.definition if info else None, unit=info.unit if info else None,
                possible_range=info.possible_range if info else None))
        out.append(MoctezumaSide(side=side, label=labels.sides.get(side, side),
                                 definition=labels.side_info.get(side),
                                 weight=p["side_weights"][side], dimensions=dims))
    return out


def _ranges(cohort: list, section: str = "moctezuma") -> dict[str, MoctezumaRange]:
    out = {}
    for dim in analytics_params(section)["dimensions"]:
        values = [v for s in cohort if (v := (s.components.get(dim) or {}).get("raw")) is not None]
        out[dim] = MoctezumaRange(observed_min=min(values, default=None),
                                  observed_max=max(values, default=None), with_data=len(values))
    return out


def _item(s: MoctezumaScore, method: Methodology) -> MoctezumaItem:
    conf = app_config()
    labels = conf.moctezuma
    occ = _occupation(s.occupation_code)
    components = [MoctezumaComponent(
        dimension=dim, label=labels.dimensions.get(dim, dim), side=c["side"], weight=c["weight"],
        raw=c["raw"], normalized=c["normalized"], indicator=c["indicator"], scope=c["scope"],
        measure=c["measure"], detail=c.get("detail") or {}, available=c["normalized"] is not None,
    ) for dim, c in s.components.items()]
    return MoctezumaItem(
        occupation=OccupationItem.model_validate(occ.model_dump()), sector_name=_sector_name(occ),
        country_iso3=s.country_iso3, year=s.year, score=s.score, level=s.level,
        level_label=labels.levels[s.level], pace=s.pace, readiness=s.readiness, gap=s.gap,
        pace_coverage=s.pace_coverage, readiness_coverage=s.readiness_coverage,
        components=components, data_type="calculated",
        data_type_label=conf.data_types["calculated"], computed_at=s.computed_at,
        methodology=_ref(method),
    )


@router.get("/moctezuma", response_model=MoctezumaPage)
def moctezuma(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    sector: str | None = None,
    occupation: str | None = None,
    featured: bool | None = Query(None, description="true: solo las ocupaciones destacadas"),
    year: int | None = Query(None, description="Año de referencia (default: el último)"),
    view: View = Query("top", description="top: mayor asimetría · bottom: menor · all: todas"),
    limit: int | None = Query(None, ge=1, le=_pagination.max_limit,
                              description="Default: ranking_size para top/bottom, default_limit para all"),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Moctezuma indicator per occupation and country: pace of technological change vs capacity
    to respond. top lists the largest asymmetries, bottom the smallest; all lists every row,
    those without a score last."""
    method = _current_method(session)
    page_size = limit or (_pagination.default_limit if view == "all" else _pagination.ranking_size)
    side_labels = app_config().moctezuma.sides
    if method is None:
        return MoctezumaPage(year=None, available_years=[], view=view, side_labels=side_labels,
                             level_labels=app_config().moctezuma.levels,
                             sides=_sides(), total=0, scored_total=0, limit=page_size,
                             offset=offset, items=[])
    years = sorted(set(session.scalars(select(MoctezumaScore.year).where(
        MoctezumaScore.methodology_id == method.methodology_id)).all()))
    year = year or (years[-1] if years else None)
    codes = [o.occupation_code for o in catalog().occupations
             if (not sector or o.sector_code == sector)
             and (featured is None or o.is_featured == featured)
             and (not occupation or o.occupation_code == occupation)]
    rows = session.scalars(select(MoctezumaScore).where(
        MoctezumaScore.methodology_id == method.methodology_id, MoctezumaScore.year == year,
        MoctezumaScore.country_iso3.in_(_country_list(country)),
        MoctezumaScore.occupation_code.in_(codes))).all()
    scored = sorted((s for s in rows if s.score is not None),
                    key=lambda s: (s.score, s.country_iso3, s.occupation_code),
                    reverse=view != "bottom")
    if view == "all":
        ordered = scored + sorted((s for s in rows if s.score is None),
                                  key=lambda s: (s.level == NOT_APPLICABLE, s.country_iso3,
                                                 s.occupation_code))
    else:
        ordered = scored
    cohort = session.scalars(select(MoctezumaScore).where(
        MoctezumaScore.methodology_id == method.methodology_id, MoctezumaScore.year == year,
        MoctezumaScore.level != NOT_APPLICABLE)).all()
    return MoctezumaPage(
        year=year, available_years=years, view=view, side_labels=side_labels,
        level_labels=app_config().moctezuma.levels, sides=_sides(),
        dimension_ranges=_ranges(cohort), total=len(rows),
        scored_total=len(scored), limit=page_size, offset=offset,
        items=[_item(s, method) for s in ordered[offset:offset + page_size]])


@router.get("/moctezuma/countries", response_model=list[MoctezumaCountry])
def moctezuma_countries(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    session: Session = Depends(get_session),
):
    """Country value per year: simple mean of the indicator, pace and readiness over the
    country's occupations with a score (every occupation weighs the same)."""
    method = _current_method(session)
    labels = app_config().moctezuma.levels
    levels = analytics_params("moctezuma")["levels"]
    out = []
    for iso3 in _country_list(country):
        rows = [] if method is None else session.scalars(select(MoctezumaScore).where(
            MoctezumaScore.methodology_id == method.methodology_id,
            MoctezumaScore.country_iso3 == iso3, MoctezumaScore.level != NOT_APPLICABLE,
        )).all()
        by_year: dict[int, list[MoctezumaScore]] = {}
        for s in rows:
            by_year.setdefault(s.year, []).append(s)
        points = []
        for year in sorted(by_year):
            scored = [s for s in by_year[year] if s.score is not None]
            if not scored:
                continue
            score = sum(s.score for s in scored) / len(scored)
            level = level_for(score, levels)
            points.append(MoctezumaCountryPoint(
                year=year, score=score, pace=sum(s.pace for s in scored) / len(scored),
                readiness=sum(s.readiness for s in scored) / len(scored), level=level,
                level_label=labels[level], scored=len(scored), total=len(by_year[year])))
        out.append(MoctezumaCountry(country_iso3=iso3, points=points,
                                    methodology=_ref(method) if method else None))
    return out


@router.get("/moctezuma/history", response_model=list[MoctezumaHistory])
def moctezuma_history(
    occupation: str,
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    session: Session = Depends(get_session),
):
    _occupation(occupation)
    method = _current_method(session)
    labels = app_config().moctezuma.levels
    out = []
    for iso3 in _country_list(country):
        rows = [] if method is None else session.scalars(select(MoctezumaScore).where(
            MoctezumaScore.methodology_id == method.methodology_id,
            MoctezumaScore.occupation_code == occupation, MoctezumaScore.country_iso3 == iso3,
        ).order_by(MoctezumaScore.year)).all()
        out.append(MoctezumaHistory(
            occupation_code=occupation, country_iso3=iso3,
            points=[MoctezumaHistoryPoint(year=s.year, score=s.score, level=s.level,
                                          level_label=labels[s.level], pace=s.pace,
                                          readiness=s.readiness) for s in rows],
            methodology=_ref(method) if method else None,
        ))
    return out


def _historical_score(pace: float, readiness: float) -> float:
    """Same formula and side weights as the indicator."""
    p = analytics_params("moctezuma")
    w = p["side_weights"]
    return (w["pace"] * pace + w["readiness"] * (p["scale_max"] - readiness)) \
        / (w["pace"] + w["readiness"])


@router.get("/moctezuma/reference", response_model=MoctezumaReference)
def moctezuma_reference():
    """Illustrative 1518-1605 version (central Mexico, config/reference) computed with the
    indicator's formula, its sources, a lower estimate for comparison, and the example settings."""
    labels = app_config().moctezuma
    h = historical_config(labels.history_file)
    top = analytics_params("moctezuma")["scale_max"]
    base = dict(h.population)[h.base_year]
    points = []
    for year, pop in h.population:
        pace = h.pace.full if year >= h.pace.full_from else h.pace.before
        readiness = pop / base * top
        points.append(MoctezumaHistoricalPoint(year=year, population=pop, pace=pace,
                                               readiness=readiness,
                                               score=_historical_score(pace, readiness)))
    alt = h.alternative
    alt_readiness = alt.compare[1] / alt.base[1] * top
    alt_pace = h.pace.full if alt.compare[0] >= h.pace.full_from else h.pace.before
    return MoctezumaReference(
        region=h.region, contact_year=h.contact_year, pace_full_from=h.pace.full_from,
        pace_note=h.pace.note, population_unit=h.population_unit, base_year=h.base_year,
        points=points, example_year=h.example_year,
        alternative=MoctezumaAlternativePoint(
            label=alt.label, base_year=alt.base[0], base_population=alt.base[1],
            year=alt.compare[0], population=alt.compare[1], readiness=alt_readiness,
            score=_historical_score(alt_pace, alt_readiness)),
        sources={**{k: [LuditaSource(**s.model_dump()) for s in v] for k, v in h.sources.items()},
                 "events": [LuditaSource(**s.model_dump()) for s in h.event_sources]},
        events=[MoctezumaEvent(**e.model_dump()) for e in h.events], point_notes=h.point_notes,
        point_labels=h.point_labels,
        side_history=labels.side_history, example_occupation=labels.example_occupation,
    )
