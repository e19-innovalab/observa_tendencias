from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.employability import level_for
from app.analytics.employability_run import NOT_APPLICABLE, _load_points
from app.analytics.ludita_run import SECTION, sides
from app.analytics.motion import roll_up
from app.analytics.recompute import params_digest
from app.api.v1.employability import View, _occupation, _ref, _sector_name
from app.api.v1.indicators import _country_list
from app.api.v1.moctezuma import _ranges, _sides
from app.api.v1.motion import _source_digits
from app.core.config_files import analytics_params, app_config, catalog, ludita_history
from app.core.database import get_session
from app.models import LuditaScore, Methodology
from app.schemas.observatory import (
    LuditaCase,
    LuditaCasePoint,
    LuditaCountry,
    LuditaCountryPoint,
    LuditaHistory,
    LuditaItem,
    LuditaPage,
    LuditaPath,
    LuditaSource,
    MoctezumaComponent,
    OccupationItem,
)

router = APIRouter(tags=["ludita"])
_pagination = app_config().pagination


def _current_method(session: Session) -> Methodology | None:
    """Scores shown are those of the parameter set currently in config/analytics.yaml."""
    digest = params_digest("ludita_index")[2]
    return session.scalar(select(Methodology).where(
        Methodology.methodology_type == "ludita_index", Methodology.params_hash == digest))


def _paths() -> list[LuditaPath]:
    return [LuditaPath(path=k, label=v.label, short=v.short, description=v.description)
            for k, v in app_config().ludita.paths.items()]


def _item(s: LuditaScore, method: Methodology) -> LuditaItem:
    conf = app_config()
    labels = conf.ludita
    occ = _occupation(s.occupation_code)
    components = [MoctezumaComponent(
        dimension=dim, label=labels.dimensions.get(dim, dim), side=c["side"], weight=c["weight"],
        raw=c["raw"], normalized=c["normalized"], indicator=c["indicator"], scope=c["scope"],
        measure=c["measure"], detail=c.get("detail") or {}, available=c["normalized"] is not None,
    ) for dim, c in s.components.items()]
    return LuditaItem(
        occupation=OccupationItem.model_validate(occ.model_dump()), sector_name=_sector_name(occ),
        country_iso3=s.country_iso3, year=s.year, score=s.score, level=s.level,
        level_label=labels.levels[s.level], path=s.path,
        path_label=labels.paths[s.path].label if s.path else None, exposure=s.exposure,
        vitality=s.vitality, exposure_coverage=s.exposure_coverage,
        vitality_coverage=s.vitality_coverage, components=components, data_type="calculated",
        data_type_label=conf.data_types["calculated"], computed_at=s.computed_at,
        methodology=_ref(method),
    )


@router.get("/ludita", response_model=LuditaPage)
def ludita(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    sector: str | None = None,
    occupation: str | None = None,
    featured: bool | None = Query(None, description="true: solo las ocupaciones destacadas"),
    path: str | None = Query(None, description="weaver | teller | other_causes | out_of_reach"),
    year: int | None = Query(None, description="Año de referencia (default: el último)"),
    view: View = Query("top", description="top: más parecido · bottom: menos · all: todas"),
    limit: int | None = Query(None, ge=1, le=_pagination.max_limit,
                              description="Default: ranking_size para top/bottom, default_limit para all"),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Ludita indicator per occupation and country: exposure to generative AI against the
    market's vitality (employment and training growth), and the path each occupation follows."""
    method = _current_method(session)
    page_size = limit or (_pagination.default_limit if view == "all" else _pagination.ranking_size)
    labels = app_config().ludita
    rules = {k: v for k, v in analytics_params(SECTION)["paths"].items() if isinstance(v, float | int)}
    base = dict(view=view, side_labels=labels.sides, level_labels=labels.levels,
                sides=_sides(SECTION), paths=_paths(),
                path_rules=rules, limit=page_size, offset=offset)
    if method is None:
        return LuditaPage(year=None, available_years=[], total=0, scored_total=0, items=[], **base)
    years = sorted(set(session.scalars(select(LuditaScore.year).where(
        LuditaScore.methodology_id == method.methodology_id)).all()))
    year = year or (years[-1] if years else None)
    codes = [o.occupation_code for o in catalog().occupations
             if (not sector or o.sector_code == sector)
             and (featured is None or o.is_featured == featured)
             and (not occupation or o.occupation_code == occupation)]
    stmt = select(LuditaScore).where(
        LuditaScore.methodology_id == method.methodology_id, LuditaScore.year == year,
        LuditaScore.country_iso3.in_(_country_list(country)),
        LuditaScore.occupation_code.in_(codes))
    if path:
        stmt = stmt.where(LuditaScore.path == path)
    rows = session.scalars(stmt).all()
    scored = sorted((s for s in rows if s.score is not None),
                    key=lambda s: (s.score, s.country_iso3, s.occupation_code),
                    reverse=view != "bottom")
    ordered = scored if view != "all" else scored + sorted(
        (s for s in rows if s.score is None),
        key=lambda s: (s.level == NOT_APPLICABLE, s.country_iso3, s.occupation_code))
    cohort = session.scalars(select(LuditaScore).where(
        LuditaScore.methodology_id == method.methodology_id, LuditaScore.year == year,
        LuditaScore.level != NOT_APPLICABLE)).all()
    return LuditaPage(
        year=year, available_years=years, dimension_ranges=_ranges(cohort, SECTION),
        total=len(rows), scored_total=len(scored),
        items=[_item(s, method) for s in ordered[offset:offset + page_size]], **base)


@router.get("/ludita/countries", response_model=list[LuditaCountry])
def ludita_countries(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    session: Session = Depends(get_session),
):
    """Country value per year: simple mean of the indicator, exposure and vitality over the
    country's occupations with a score, and how many occupations follow each path."""
    method = _current_method(session)
    labels = app_config().ludita.levels
    levels = analytics_params(SECTION)["levels"]
    push, counter = sides()
    out = []
    for iso3 in _country_list(country):
        rows = [] if method is None else session.scalars(select(LuditaScore).where(
            LuditaScore.methodology_id == method.methodology_id,
            LuditaScore.country_iso3 == iso3, LuditaScore.level != NOT_APPLICABLE,
        )).all()
        by_year: dict[int, list[LuditaScore]] = {}
        for s in rows:
            by_year.setdefault(s.year, []).append(s)
        points = []
        for year in sorted(by_year):
            scored = [s for s in by_year[year] if s.score is not None]
            if not scored:
                continue
            score = sum(s.score for s in scored) / len(scored)
            level = level_for(score, levels)
            paths = {k: sum(s.path == k for s in scored) for k in app_config().ludita.paths}
            points.append(LuditaCountryPoint(
                year=year, score=score, exposure=sum(getattr(s, push) for s in scored) / len(scored),
                vitality=sum(getattr(s, counter) for s in scored) / len(scored), level=level,
                level_label=labels[level], scored=len(scored), total=len(by_year[year]),
                paths=paths))
        out.append(LuditaCountry(country_iso3=iso3, points=points,
                                 methodology=_ref(method) if method else None))
    return out


def _case_points(series: list[tuple[int, float, bool, str | None]], arrival: int,
                 base_year: int) -> list[LuditaCasePoint]:
    base = next(v for y, v, _, _ in series if y == base_year)
    return [LuditaCasePoint(year=y, years_since=y - arrival, value=v, index=v / base * 100,
                            approx=approx, note=note) for y, v, approx, note in series]


@router.get("/ludita/history", response_model=LuditaHistory)
def ludita_history_curves(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    session: Session = Depends(get_session),
):
    """Employment of the historical cases (weavers, telephone operators, bank tellers) and of
    today's most exposed occupation groups, each indexed to 100 at its technology's arrival."""
    conf = app_config().ludita.history
    cases = [LuditaCase(
        key=k, label=c.label, technology=c.technology, arrival_year=c.arrival_year,
        arrival_note=c.arrival_note, base_year=c.base_year, path=c.path,
        source_short=c.source_short, points=_case_points([(p.year, p.value, p.approx, p.note) for p in c.series],
                            c.arrival_year, c.base_year),
        sources=[LuditaSource(**s.model_dump()) for s in c.sources],
    ) for k, c in ludita_history(conf.file).items()]

    t = conf.today
    countries = _country_list(country)
    raw = _load_points(session, {t.indicator})
    points = {(c, occ): pts for (_, c, occ), pts in raw.items() if c in countries}
    rolled = roll_up(points, _source_digits(t.indicator, countries), t.group_digits, "sum")
    today = []
    for iso3 in countries:
        for group in t.groups:
            series = sorted((y, v, False, None) for (c, g, y), v in rolled.items()
                            if c == iso3 and g == group and y >= t.arrival_year)
            if not series or series[0][0] != t.arrival_year:
                continue
            today.append(LuditaCase(
                key=f"today-{iso3}-{group}", label=t.label, technology=t.technology,
                arrival_year=t.arrival_year, arrival_note=t.arrival_note,
                base_year=t.arrival_year, path=None, source_short=t.source_short,
                country_iso3=iso3,
                points=_case_points(series, t.arrival_year, t.arrival_year)))
    return LuditaHistory(zoom_years=conf.zoom_years, cases=cases, today=today)
