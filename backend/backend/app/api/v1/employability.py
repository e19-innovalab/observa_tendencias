import unicodedata
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.employability import level_for
from app.analytics.employability_run import NOT_APPLICABLE
from app.analytics.recompute import params_digest
from app.api.v1.indicators import _country_list
from app.core.config_files import analytics_params, app_config, catalog, indicators
from app.core.database import get_session
from app.models import EmployabilityScore, Methodology, Observation
from app.normalization.periods import period_label
from app.schemas.observatory import (
    DimensionRange,
    DisplayValue,
    EmployabilityComponent,
    EmployabilityHistory,
    EmployabilityHistoryPoint,
    EmployabilityItem,
    EmployabilityPage,
    EmployabilityTexts,
    MethodologyRef,
    OccupationGroup,
    OccupationItem,
    OccupationProfile,
    SectorsPage,
    SectorSummary,
    SectorTopOccupation,
)
from app.services.observations import latest_pair, query_points

router = APIRouter(tags=["employability"])
_pagination = app_config().pagination
View = Literal["top", "bottom", "all"]
Order = Literal["asc", "desc"]


def _current_method(session: Session) -> Methodology | None:
    """Scores shown are those of the parameter set currently in config/analytics.yaml."""
    digest = params_digest("employability_index")[2]
    return session.scalar(select(Methodology).where(
        Methodology.methodology_type == "employability_index", Methodology.params_hash == digest))


def _ref(m: Methodology) -> MethodologyRef:
    return MethodologyRef(methodology_id=m.methodology_id, methodology_type=m.methodology_type,
                          version=m.version, name=m.name)


def _occupation(code: str):
    occ = catalog().occupation(code)
    if occ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            app_config().messages["unknown_occupation"].format(code=code))
    return occ


def _sector_name(occ) -> str | None:
    return next((x.name for x in catalog().sectors if x.sector_code == occ.sector_code), None)


def _group_code(occupation_code: str) -> str:
    return occupation_code[:app_config().employability.ranking.group_digits]


def _cap_per_group(rows: list[EmployabilityScore]) -> tuple[list[EmployabilityScore], dict]:
    """Keep at most max_per_group rows per ISCO group (in order). Returns the kept rows and,
    per kept row id, how many of its group were left out."""
    conf = app_config().employability.ranking
    seen: dict[tuple, list[int]] = {}
    kept, hidden = [], {}
    for s in rows:
        key = (_group_code(s.occupation_code),) + ((s.country_iso3,)
                                                    if conf.group_scope == "country" else ())
        members = seen.setdefault(key, [])
        if len(members) < conf.max_per_group:
            kept.append(s)
            members.append(s.score_id)
        hidden[key] = hidden.get(key, 0) + (len(members) >= conf.max_per_group
                                            and s.score_id not in members)
    per_row = {}
    for key, ids in seen.items():
        for sid in ids:
            per_row[sid] = hidden.get(key, 0)
    return kept, per_row


def _texts() -> EmployabilityTexts:
    labels = app_config().employability
    return EmployabilityTexts(terms=labels.terms, unit_formats=labels.unit_formats,
                              display={d: {"label": v.label, "note": v.note}
                                       for d, v in labels.display_values.items()})


DisplayLookup = dict[tuple[str, str, str, str], float]


def _display_lookup(session: Session, rows: list[EmployabilityScore]) -> DisplayLookup:
    """Values of app.yaml employability.display_values for these rows, keyed by (dimension,
    country, occupation, period): one query for the whole page."""
    shown = app_config().employability.display_values
    if not shown or not rows:
        return {}
    by_indicator: dict[str, list[str]] = {}
    for dim, conf in shown.items():
        by_indicator.setdefault(conf.indicator, []).append(dim)
    stmt = select(Observation).where(
        Observation.indicator_code.in_(list(by_indicator)),
        Observation.country_iso3.in_({s.country_iso3 for s in rows}),
        Observation.occupation_code.in_({s.occupation_code for s in rows}),
        Observation.sector_code.is_(None), Observation.data_type == "observed")
    out: DisplayLookup = {}
    for o in session.scalars(stmt).all():
        for dim in by_indicator[o.indicator_code]:
            out[(dim, o.country_iso3, o.occupation_code, period_label(o.period_start, o.frequency))] = o.value
    return out


def _display(dim: str, s: EmployabilityScore, c: dict, lookup: DisplayLookup) -> DisplayValue | None:
    """The display value for the same period the index used for this dimension."""
    conf = app_config().employability.display_values.get(dim)
    period = (c.get("detail") or {}).get("period")
    value = lookup.get((dim, s.country_iso3, s.occupation_code, period)) if conf and period else None
    if value is None:
        return None
    return DisplayValue(indicator=conf.indicator, label=conf.label, unit=indicators().get(conf.indicator).unit,
                        value=value, period=period, note=conf.note)


def _item(s: EmployabilityScore, method: Methodology,
          group_hidden: int | None = None, lookup: DisplayLookup | None = None) -> EmployabilityItem:
    conf = app_config()
    occ = _occupation(s.occupation_code)
    components = []
    for dim, c in s.components.items():
        ind = indicators().get(c["indicator"]) if c.get("indicator") else None
        components.append(EmployabilityComponent(
            dimension=dim, label=conf.employability.dimensions.get(dim, dim), weight=c["weight"],
            raw=c["raw"], normalized=c["normalized"], contribution=c.get("contribution"),
            indicator=c.get("indicator"), unit=ind.unit if ind else None, measure=c["measure"],
            detail=c.get("detail") or {}, available=c["normalized"] is not None,
            display=_display(dim, s, c, lookup or {}),
        ))
    return EmployabilityItem(
        occupation=OccupationItem.model_validate(occ.model_dump()), sector_name=_sector_name(occ),
        country_iso3=s.country_iso3, year=s.year, score=s.score, level=s.level,
        level_label=conf.employability.levels[s.level], coverage_ratio=s.coverage_ratio,
        components=components, data_type="calculated",
        data_type_label=conf.data_types["calculated"], computed_at=s.computed_at,
        methodology=_ref(method), group_code=_group_code(s.occupation_code),
        group_hidden=group_hidden,
    )


# Text fields sort alphabetically and start A->Z; numeric fields start high to low.
TEXT_SORTS = ("occupation", "isco", "country")
EXTRA_NUMERIC_SORTS = ("coverage",)


def _text_key(text: str) -> str:
    """Case- and accent-insensitive key, so "Ópticos" sorts under O."""
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold())
                   if unicodedata.category(c) != "Mn")


def _sort_value(s: EmployabilityScore, sort_by: str) -> float | str | None:
    if sort_by == "score":
        return s.score
    if sort_by == "occupation":
        return _text_key(catalog().occupation(s.occupation_code).name)
    if sort_by == "isco":
        return s.occupation_code
    if sort_by == "country":
        return s.country_iso3
    if sort_by == "coverage":
        return s.coverage_ratio
    component = s.components.get(sort_by) or {}
    return component.get("raw")


@router.get("/employability", response_model=EmployabilityPage)
def employability(
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    sector: str | None = None,
    occupation: str | None = None,
    featured: bool | None = Query(None, description="true: solo las ocupaciones destacadas"),
    q: str | None = Query(None, description="Texto a buscar en el nombre o el código CIUO"),
    year: int | None = Query(None, description="Año de referencia (default: el último)"),
    view: View = Query("top", description="top: mejores · bottom: peores · all: todas"),
    sort_by: str = Query("score", description="score, una dimensión (net_demand, salary_ppp, "
                                              "insertion_rate, automation_risk), coverage, "
                                              "occupation (nombre), isco (código CIUO) o country"),
    order: Order | None = Query(None, description="asc | desc (default: desc para números, asc "
                                                  "para texto; bottom invierte)"),
    limit: int | None = Query(None, ge=1, le=_pagination.max_limit,
                              description="Default: ranking_size para top/bottom, default_limit para all"),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Employability index for the whole occupation universe, sortable by score or by any
    dimension's raw value. top/bottom list rows that have a value for the sort field (bottom
    reverses the order); all lists every row, those without a value last."""
    options = ["score", *analytics_params("employability")["dimensions"], *EXTRA_NUMERIC_SORTS,
               *TEXT_SORTS]
    if sort_by not in options:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, app_config().messages[
            "invalid_sort"].format(field=sort_by, options=", ".join(options)))
    natural = "asc" if sort_by in TEXT_SORTS else "desc"
    order = order or (natural if view != "bottom" else ("desc" if natural == "asc" else "asc"))
    method = _current_method(session)
    page_size = limit or (_pagination.default_limit if view == "all" else _pagination.ranking_size)
    if method is None:
        return EmployabilityPage(year=None, available_years=[], view=view, sort_by=sort_by,
                                 order=order, total=0, scored_total=0, limit=page_size,
                                 offset=offset, dimension_ranges=[], items=[])
    years = sorted(set(session.scalars(select(EmployabilityScore.year).where(
        EmployabilityScore.methodology_id == method.methodology_id)).all()))
    year = year or (years[-1] if years else None)
    stmt = select(EmployabilityScore).where(
        EmployabilityScore.methodology_id == method.methodology_id, EmployabilityScore.year == year)
    filtered = stmt.where(EmployabilityScore.country_iso3.in_(_country_list(country)))
    codes = [o.occupation_code for o in catalog().occupations
             if (not sector or o.sector_code == sector)
             and (featured is None or o.is_featured == featured)
             and (not q or q.lower() in o.name.lower() or q.lower() in (o.name_en or "").lower()
                  or o.occupation_code.startswith(q))
             and (not occupation or o.occupation_code == occupation)]
    rows = session.scalars(filtered.where(EmployabilityScore.occupation_code.in_(codes))).all()
    with_value = sorted((s for s in rows if _sort_value(s, sort_by) is not None),
                        key=lambda s: (_sort_value(s, sort_by), s.country_iso3, s.occupation_code),
                        reverse=order == "desc")
    hidden: dict = {}
    if view != "all":
        # rankings: only occupations that apply to the region, and (for numeric sorts) at most
        # max_per_group per ISCO group so one family does not fill the list
        with_value = [s for s in with_value if s.level != NOT_APPLICABLE]
        if sort_by in TEXT_SORTS:
            with_value = [s for s in with_value if s.score is not None]
        else:
            with_value, hidden = _cap_per_group(with_value)
    without = sorted((s for s in rows if _sort_value(s, sort_by) is None),
                     key=lambda s: (s.country_iso3, s.occupation_code))
    ordered = with_value + without if view == "all" else with_value
    page = ordered[offset:offset + page_size]
    lookup = _display_lookup(session, page)
    cohort = [s for s in session.scalars(stmt).all() if s.level != NOT_APPLICABLE]
    ranges = _dimension_ranges(cohort)
    return EmployabilityPage(
        year=year, available_years=years, view=view, sort_by=sort_by, order=order,
        total=len(rows), scored_total=sum(s.score is not None for s in rows), limit=page_size,
        offset=offset, dimension_ranges=ranges, no_source_note=_no_source_note(ranges),
        items=[_item(s, method, hidden.get(s.score_id), lookup) for s in page])


def _pct(share: float) -> str:
    return f"{share * 100:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " %"


def _no_source_note(ranges: list[DimensionRange]) -> str | None:
    template = app_config().employability.no_source_note
    missing = [r for r in ranges if not r.has_source]
    if not template or not missing:
        return None
    return template.format(
        dimensions=", ".join(f"{r.label} ({_pct(r.weight)})" for r in missing),
        weights=", ".join(f"{r.label} {_pct(r.weight)} → {_pct(r.effective_weight)}"
                          for r in ranges if r.has_source),
        min_coverage=_pct(analytics_params("employability")["min_coverage"]))


def _dimension_ranges(cohort: list[EmployabilityScore]) -> list[DimensionRange]:
    p = analytics_params("employability")
    labels = app_config().employability
    sourced = {d for d, conf in p["dimensions"].items() if conf.get("indicator")}
    sourced_weight = sum(w for d, w in p["weights"].items() if d in sourced)
    out = []
    for dim, weight in p["weights"].items():
        values = [v for s in cohort if (v := (s.components.get(dim) or {}).get("raw")) is not None]
        info = labels.dimension_info.get(dim)
        out.append(DimensionRange(
            dimension=dim, label=labels.dimensions.get(dim, dim), weight=weight,
            higher_is_better=p["higher_is_better"][dim],
            definition=info.definition if info else None, unit=info.unit if info else None,
            possible_range=info.possible_range if info else None,
            observed_min=min(values) if values else None,
            observed_max=max(values) if values else None,
            with_data=len(values), total=len(cohort), has_source=dim in sourced,
            source_status=info.source_status if info and dim not in sourced else None,
            effective_weight=weight / sourced_weight if dim in sourced and sourced_weight else 0.0,
        ))
    return out


def _mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


@router.get("/employability/sectors", response_model=SectorsPage)
def employability_sectors(
    country: str | None = Query(None, description="ISO3; varios separados por coma (default: los 3)"),
    year: int | None = Query(None, description="Año de referencia (default: el último)"),
    session: Session = Depends(get_session),
):
    """The index by strategic sector: average score of the sector's occupations, the leading
    occupation, average salary and AI exposure, and the average of each dimension (0-100), with
    the change from the previous year. Occupations are placed in sectors by
    config/reference/isco_sectors.yaml (featured ones by catalog.yaml)."""
    method = _current_method(session)
    countries = _country_list(country)
    if method is None:
        return SectorsPage(year=None, available_years=[], countries=countries, regional_average=None,
                           dimension_ranges=[], no_source_note=None, items=[])
    years = sorted(set(session.scalars(select(EmployabilityScore.year).where(
        EmployabilityScore.methodology_id == method.methodology_id)).all()))
    year = year or (years[-1] if years else None)
    previous = max((y for y in years if year is not None and y < year), default=None)
    rows = session.scalars(select(EmployabilityScore).where(
        EmployabilityScore.methodology_id == method.methodology_id,
        EmployabilityScore.year.in_([y for y in (year, previous) if y is not None]),
        EmployabilityScore.country_iso3.in_(countries))).all()
    p = analytics_params("employability")
    labels = app_config().employability.levels
    by_sector: dict[str, list[str]] = {}
    for occ in catalog().occupations:
        if occ.sector_code and not occ.is_excluded:
            by_sector.setdefault(occ.sector_code, []).append(occ.occupation_code)
    items, sector_rows = [], []
    lookup = _display_lookup(session, [s for s in rows if s.year == year])
    for sector in catalog().sectors:
        codes = set(by_sector.get(sector.sector_code, []))
        current = [s for s in rows if s.year == year and s.occupation_code in codes
                   and s.score is not None and s.level != NOT_APPLICABLE]
        before = [s.score for s in rows if s.year == previous and s.occupation_code in codes
                  and s.score is not None and s.level != NOT_APPLICABLE]
        sector_rows += current
        avg, prev = _mean(s.score for s in current), _mean(before)
        best = max(current, key=lambda s: s.score, default=None)
        level = level_for(avg, p["levels"]) if avg is not None else None
        items.append(SectorSummary(
            sector_code=sector.sector_code, name=sector.name, occupations=len(codes),
            scored=len(current), average_score=avg, previous_average=prev,
            change=avg - prev if avg is not None and prev is not None else None,
            level=level, level_label=labels.get(level) if level else None,
            top_occupation=SectorTopOccupation(
                occupation_code=best.occupation_code, name=catalog().occupation(best.occupation_code).name,
                country_iso3=best.country_iso3, score=best.score) if best else None,
            salary_ppp_average=_mean((s.components.get("salary_ppp") or {}).get("raw") for s in current),
            salary_usd_average=_mean(d.value for s in current
                                     if (d := _display("salary_ppp", s, s.components.get("salary_ppp") or {}, lookup))),
            automation_average=_mean((s.components.get("automation_risk") or {}).get("raw") for s in current),
            dimensions={d: _mean((s.components.get(d) or {}).get("normalized") for s in current)
                        for d in p["weights"]},
        ))
    cohort = [s for s in rows if s.year == year and s.level != NOT_APPLICABLE]
    ranges = _dimension_ranges(cohort)
    return SectorsPage(year=year, available_years=years, countries=countries,
                       regional_average=_mean(s.score for s in sector_rows),
                       dimension_ranges=ranges, no_source_note=_no_source_note(ranges), items=items,
                       texts=_texts())


@router.get("/employability/history", response_model=list[EmployabilityHistory])
def employability_history(
    occupation: str,
    country: str | None = Query(None, description="ISO3; varios separados por coma"),
    session: Session = Depends(get_session),
):
    _occupation(occupation)
    method = _current_method(session)
    labels = app_config().employability.levels
    out = []
    for iso3 in _country_list(country):
        rows = [] if method is None else session.scalars(
            select(EmployabilityScore).where(
                EmployabilityScore.methodology_id == method.methodology_id,
                EmployabilityScore.occupation_code == occupation,
                EmployabilityScore.country_iso3 == iso3,
            ).order_by(EmployabilityScore.year)).all()
        out.append(EmployabilityHistory(
            occupation_code=occupation, country_iso3=iso3,
            points=[EmployabilityHistoryPoint(year=s.year, score=s.score, level=s.level,
                                              level_label=labels[s.level],
                                              coverage_ratio=s.coverage_ratio) for s in rows],
            methodology=_ref(method) if method else None,
        ))
    return out


@router.get("/occupations/{code}", response_model=OccupationProfile)
def occupation_profile(code: str, session: Session = Depends(get_session)):
    """Ocupaciones screen: the occupation, the ISCO groups its figures come from (and which other
    occupations share them), its latest index per country and latest value of each indicator."""
    occ = _occupation(code)
    groups = []
    for ind in indicators().indicators:
        for s in ind.series:
            if s.occupation_dimension:
                digits = s.occupation_isco_digits
                groups.append(OccupationGroup(
                    indicator=ind.code, source=s.source,
                    countries=s.countries or [c.iso3 for c in catalog().countries],
                    group_code=f"{s.occupation_code_prefix}{occ.isco08_code[:digits]}",
                    isco_digits=digits,
                    shared_with=[o.occupation_code for o in catalog().occupations
                                 if o.isco08_code[:digits] == occ.isco08_code[:digits]
                                 and o.occupation_code != code],
                ))
    method = _current_method(session)
    employability_items = []
    if method is not None:
        latest_year = session.scalar(select(EmployabilityScore.year).where(
            EmployabilityScore.methodology_id == method.methodology_id
        ).order_by(EmployabilityScore.year.desc()))
        rows = session.scalars(select(EmployabilityScore).where(
            EmployabilityScore.methodology_id == method.methodology_id,
            EmployabilityScore.occupation_code == code, EmployabilityScore.year == latest_year,
        ).order_by(EmployabilityScore.country_iso3)).all()
        lookup = _display_lookup(session, rows)
        employability_items = [_item(s, method, lookup=lookup) for s in rows]
    dims = analytics_params("employability")["dimensions"]
    latest = []
    for ind_code in [d["indicator"] for d in dims.values() if d.get("indicator")]:
        ind = indicators().get(ind_code)
        for iso3 in _country_list(None):
            cur, _ = latest_pair(query_points(session, ind, [iso3], occupation=code))
            if cur:
                latest.append(cur)
    from app.api.v1.graduates import isco_levels  # avoid an import cycle
    from app.api.v1.skills import occupation_skills

    _, top_skills = occupation_skills(session, code, app_config().skills.profile_top)
    return OccupationProfile(occupation=OccupationItem.model_validate(occ.model_dump()),
                             sector_name=_sector_name(occ), groups=groups,
                             employability=employability_items, latest=latest,
                             top_skills=top_skills, hierarchy=isco_levels(code), texts=_texts())
