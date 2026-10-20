"""Queries over observations shared by the indicator, compare and dashboard endpoints."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config_files import IndicatorConf, app_config
from app.models import Observation, Source
from app.normalization.periods import period_label
from app.schemas.observatory import IndicatorItem, ObservationPoint, SourceRef


def source_refs(session: Session) -> dict[int, SourceRef]:
    return {s.source_id: SourceRef(code=s.source_code, name=s.name)
            for s in session.scalars(select(Source)).all()}


def indicator_item(ind: IndicatorConf, refs: dict[int, SourceRef] | None = None) -> IndicatorItem:
    names = {r.code: r.name for r in (refs or {}).values()}
    seen: list[str] = list(dict.fromkeys(s.source for s in ind.series))
    return IndicatorItem(
        code=ind.code, name=ind.name, unit=ind.unit, domain=ind.domain,
        domain_label=app_config().domains[ind.domain],
        higher_is_better=ind.higher_is_better, description=ind.description,
        sources=[SourceRef(code=c, name=names.get(c, c)) for c in seen],
        has_sector_breakdown=any(s.sector_dimension for s in ind.series),
    )


def to_point(o: Observation, refs: dict[int, SourceRef]) -> ObservationPoint:
    return ObservationPoint(
        indicator_code=o.indicator_code, country_iso3=o.country_iso3,
        sector_code=o.sector_code, occupation_code=o.occupation_code,
        period=period_label(o.period_start, o.frequency),
        period_start=o.period_start, period_end=o.period_end, frequency=o.frequency,
        value=o.value, unit=o.unit, data_type=o.data_type,
        data_type_label=app_config().data_types[o.data_type],
        lower_bound=o.lower_bound, upper_bound=o.upper_bound,
        source=refs[o.source_id], source_updated_at=o.source_updated_at,
        fetched_at=o.fetched_at, methodology_id=o.methodology_id,
    )


def query_points(
    session: Session,
    ind: IndicatorConf,
    countries: list[str] | None = None,
    sector: str | None = None,
    occupation: str | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    data_type: str | None = None,
    limit: int | None = None,
) -> list[ObservationPoint]:
    """Points for one indicator. Without sector/occupation, national totals are returned.

    When several sources feed the same indicator, the first source listed in
    config/indicators.yaml wins for each (country, sector, occupation, period, data_type).
    """
    stmt = select(Observation).where(Observation.indicator_code == ind.code)
    if countries:
        stmt = stmt.where(Observation.country_iso3.in_([c.upper() for c in countries]))
    stmt = stmt.where(
        Observation.sector_code == sector if sector else Observation.sector_code.is_(None),
        Observation.occupation_code == occupation if occupation
        else Observation.occupation_code.is_(None),
    )
    if from_year:
        stmt = stmt.where(Observation.period_start >= date(from_year, 1, 1))
    if to_year:
        stmt = stmt.where(Observation.period_start <= date(to_year, 12, 31))
    if data_type:
        stmt = stmt.where(Observation.data_type == data_type)
    stmt = stmt.order_by(Observation.country_iso3, Observation.period_start)

    refs = source_refs(session)
    priority = {code: i for i, code in enumerate(dict.fromkeys(s.source for s in ind.series))}
    best: dict[tuple, Observation] = {}
    for o in session.scalars(stmt).all():
        key = (o.country_iso3, o.sector_code, o.occupation_code, o.period_start, o.data_type)
        rank = priority.get(refs[o.source_id].code, len(priority))
        current = best.get(key)
        if current is None or rank < priority.get(refs[current.source_id].code, len(priority)):
            best[key] = o
    points = [to_point(o, refs) for o in best.values()]
    points.sort(key=lambda p: (p.country_iso3, p.period_start))
    return points[:limit] if limit else points


def latest_pair(
    points: list[ObservationPoint],
) -> tuple[ObservationPoint | None, ObservationPoint | None]:
    observed = sorted((p for p in points if p.data_type == "observed"), key=lambda p: p.period_start)
    if not observed:
        return None, None
    return observed[-1], observed[-2] if len(observed) > 1 else None


def change_kind_for(unit: str, requested: str | None = None) -> str:
    if requested:
        return requested
    return "absolute" if unit in app_config().comparison.absolute_units else "relative"


def compute_change(
    current: ObservationPoint | None, previous: ObservationPoint | None, kind: str
) -> float | None:
    if current is None or previous is None:
        return None
    if kind == "absolute":
        return current.value - previous.value
    if previous.value == 0:
        return None
    return (current.value - previous.value) / abs(previous.value)
