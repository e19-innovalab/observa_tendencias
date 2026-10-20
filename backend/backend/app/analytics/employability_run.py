"""Build the employability index (ISE) from observations and store it per reference year.

Dimensions, their source indicators, measures and weights come from config/analytics.yaml
(section employability). For each reference year every (country, occupation) gets each
dimension's raw value as of that year; compute_employability_index scales them within the
cohort, redistributes missing weight and reports coverage.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics.employability import compute_employability_index
from app.core.config_files import analytics_params, catalog
from app.models import EmployabilityScore, Methodology, Observation, Source

NOT_APPLICABLE = "not_applicable"


@dataclass
class Point:
    year: int
    value: float
    source: str
    source_updated_at: date | None


def input_indicators() -> set[str]:
    dims = analytics_params("employability")["dimensions"]
    return {d["indicator"] for d in dims.values() if d.get("indicator")}


def _load_points(session: Session, codes: set[str]) -> dict[tuple, list[Point]]:
    """(indicator, country, occupation) -> observed points sorted by year."""
    sources = {s.source_id: s.source_code for s in session.scalars(select(Source)).all()}
    rows = session.scalars(select(Observation).where(
        Observation.indicator_code.in_(codes), Observation.occupation_code.is_not(None),
        Observation.data_type == "observed", Observation.frequency == "A",
    )).all()
    out: dict[tuple, list[Point]] = defaultdict(list)
    for o in rows:
        out[(o.indicator_code, o.country_iso3, o.occupation_code)].append(
            Point(o.period_start.year, o.value, sources[o.source_id], o.source_updated_at))
    for pts in out.values():
        pts.sort(key=lambda p: p.year)
    return out


def dimension_value(points: list[Point], conf: dict, year: int, max_age: int) -> tuple[float | None, dict]:
    """Raw value of one dimension as of `year`, plus the detail needed to trace it."""
    excluded = set(conf.get("exclude_years", []))
    if conf.get("applies_to_all_years"):
        usable = points
    else:
        usable = [p for p in points
                  if year - max_age <= p.year <= year and p.year not in excluded]
    if not usable:
        return None, {}
    last = usable[-1]
    if conf["measure"] == "latest":
        return last.value, {"period": str(last.year), "value": last.value, "source": last.source,
                            "source_updated_at": str(last.source_updated_at or "") or None}
    # growth: average annual growth between the earliest point in the window and the latest
    base = next((p for p in usable if last.year - conf["window_years"] <= p.year < last.year), None)
    if base is None or base.value <= 0 or base.value < conf.get("min_base", 0):
        return None, {}
    years = last.year - base.year
    growth = (last.value / base.value) ** (1 / years) - 1
    return growth, {"from_period": str(base.year), "to_period": str(last.year),
                    "from_value": base.value, "to_value": last.value, "source": last.source}


def recompute_employability(session: Session, method: Methodology) -> int:
    """Recalculate every reference year. Returns the number of scores stored."""
    p = analytics_params("employability")
    dims, max_age = p["dimensions"], p["max_age_years"]
    points = _load_points(session, input_indicators())
    data_years = [pt.year for (ind, *_), pts in points.items() for pt in pts
                  if not dims_for_indicator(dims, ind).get("applies_to_all_years")]
    if not data_years:
        return 0
    countries = [c.iso3 for c in catalog().countries]
    occupations = [o.occupation_code for o in catalog().occupations]
    excluded = {o.occupation_code for o in catalog().occupations if o.is_excluded}
    now = datetime.now(UTC)
    session.execute(delete(EmployabilityScore).where(
        EmployabilityScore.methodology_id == method.methodology_id))

    stored = 0
    for year in range(p["first_year"], max(data_years) + 1):
        raw: dict[tuple, dict] = {}
        detail: dict[tuple, dict] = {}
        for country in countries:
            for occ in occupations:
                key = (country, occ)
                raw[key], detail[key] = {}, {}
                for dim, conf in dims.items():
                    pts = points.get((conf.get("indicator"), country, occ), [])
                    raw[key][dim], detail[key][dim] = dimension_value(pts, conf, year, max_age)
        # occupations that do not apply to the region stay out of the cohort (they would
        # shift the min-max scaling of everyone else); they are stored without a score
        in_cohort = [k for k in raw if k[1] not in excluded]
        cohorts = [in_cohort] if p["cohort"] == "all" else [
            [k for k in in_cohort if k[0] == c] for c in countries]
        for country, occ in (k for k in raw if k[1] in excluded):
            weights = p["weights"]
            components = {
                dim: {"raw": raw[(country, occ)][dim], "normalized": None, "weight": weights[dim],
                      "indicator": dims[dim].get("indicator"), "measure": dims[dim]["measure"],
                      "contribution": None, "detail": detail[(country, occ)][dim]}
                for dim in weights
            }
            session.add(EmployabilityScore(
                country_iso3=country, occupation_code=occ, year=year, score=None,
                level=NOT_APPLICABLE, coverage_ratio=0.0, components=components,
                methodology_id=method.methodology_id, computed_at=now,
            ))
            stored += 1
        for members in cohorts:
            results = compute_employability_index({k: raw[k] for k in members}, p)
            for (country, occ), res in results.items():
                available = sum(c["weight"] for c in res["components"].values()
                                if c["normalized"] is not None)
                components = {
                    dim: {**c, "indicator": dims[dim].get("indicator"),
                          "measure": dims[dim]["measure"],
                          "contribution": (c["normalized"] * c["weight"] / available
                                           if c["normalized"] is not None and available else None),
                          "detail": detail[(country, occ)][dim]}
                    for dim, c in res["components"].items()
                }
                session.add(EmployabilityScore(
                    country_iso3=country, occupation_code=occ, year=year, score=res["score"],
                    level=res["level"], coverage_ratio=res["coverage_ratio"],
                    components=components, methodology_id=method.methodology_id,
                    computed_at=now,
                ))
                stored += 1
    return stored


def dims_for_indicator(dims: dict, indicator: str) -> dict:
    return next((c for c in dims.values() if c.get("indicator") == indicator), {})
