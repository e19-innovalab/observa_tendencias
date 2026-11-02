"""Build the Moctezuma indicator from observations and store it per reference year.

Dimensions come from config/analytics.yaml (section moctezuma). Occupation dimensions read the
occupation series (as the ISE does); country dimensions read the national series and apply to
every occupation of the country; `graduates` reads the graduates table through the skill gaps
crosswalks (the same supply the skill gaps use).
"""
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics.employability_run import NOT_APPLICABLE, Point, _load_points, dimension_value
from app.analytics.moctezuma import SIDES, compute_two_sided_index
from app.core.config_files import analytics_params, catalog
from app.models import Methodology, MoctezumaScore, Observation, Source

GRADUATES = "graduates"


def input_indicators(section: str = "moctezuma") -> set[str]:
    dims = analytics_params(section)["dimensions"]
    return {d["indicator"] for d in dims.values() if d["indicator"] != GRADUATES}


def _load_national_points(session: Session, codes: set[str]) -> dict[tuple, list[Point]]:
    """(indicator, country) -> observed national points (no sector, no occupation) by year."""
    sources = {s.source_id: s.source_code for s in session.scalars(select(Source)).all()}
    rows = session.scalars(select(Observation).where(
        Observation.indicator_code.in_(codes), Observation.occupation_code.is_(None),
        Observation.sector_code.is_(None), Observation.data_type == "observed",
        Observation.frequency == "A",
    )).all()
    out: dict[tuple, list[Point]] = defaultdict(list)
    for o in rows:
        out[(o.indicator_code, o.country_iso3)].append(
            Point(o.period_start.year, o.value, sources[o.source_id], o.source_updated_at))
    for pts in out.values():
        pts.sort(key=lambda p: p.year)
    return out


def _load_graduate_points(session: Session, countries: list[str]) -> dict[tuple, list[Point]]:
    """(graduates, country, occupation) -> graduates per year, split by the crosswalks."""
    from app.analytics.skill_gaps_run import load_crosswalk, occupation_supply  # import cycle

    crosswalks = analytics_params("skill_gaps")["crosswalks"]
    out: dict[tuple, list[Point]] = {}
    for country in countries:
        if not crosswalks.get(country):
            continue
        for occ, series in occupation_supply(session, country,
                                             load_crosswalk(crosswalks[country])).items():
            out[(GRADUATES, country, occ)] = [Point(y, v, GRADUATES, None)
                                              for y, v in sorted(series.items())]
    return out


def two_sided_results(session: Session, section: str, sides: tuple[str, str]):
    """Score every catalog occupation and country for each reference year with the two-sided
    index of the given config section. Yields (country, occupation, year, result), where
    result is compute_two_sided_index's plus each component's source (indicator, scope,
    measure, detail). Excluded occupations get not_applicable."""
    p = analytics_params(section)
    dims, max_age = p["dimensions"], p["max_age_years"]
    countries = [c.iso3 for c in catalog().countries]
    occupations = [o.occupation_code for o in catalog().occupations]
    excluded = {o.occupation_code for o in catalog().occupations if o.is_excluded}
    occ_codes = {d["indicator"] for d in dims.values()
                 if d["scope"] == "occupation" and d["indicator"] != GRADUATES}
    nat_codes = {d["indicator"] for d in dims.values() if d["scope"] == "country"}
    points = {**_load_points(session, occ_codes), **_load_national_points(session, nat_codes)}
    if any(d["indicator"] == GRADUATES for d in dims.values()):
        points.update(_load_graduate_points(session, countries))

    def series(conf: dict, country: str, occ: str) -> list[Point]:
        key = (conf["indicator"], country) if conf["scope"] == "country" \
            else (conf["indicator"], country, occ)
        return points.get(key, [])

    yearly = {d["indicator"] for d in dims.values() if not d.get("applies_to_all_years")}
    data_years = [pt.year for key, pts in points.items() if key[0] in yearly for pt in pts]
    if not data_years:
        return
    for year in range(p["first_year"], max(data_years) + 1):
        raw: dict[tuple, dict] = {}
        detail: dict[tuple, dict] = {}
        for country in countries:
            for occ in occupations:
                key = (country, occ)
                raw[key], detail[key] = {}, {}
                for dim, conf in dims.items():
                    raw[key][dim], detail[key][dim] = dimension_value(
                        series(conf, country, occ), conf, year, max_age)
        in_cohort = [k for k in raw if k[1] not in excluded]
        cohorts = [in_cohort] if p["cohort"] == "all" else [
            [k for k in in_cohort if k[0] == c] for c in countries]
        results = {k: {"score": None, "level": NOT_APPLICABLE, sides[0]: None, sides[1]: None,
                       "gap": None, "coverage": {s: 0.0 for s in sides},
                       "components": {d: {"raw": raw[k][d], "normalized": None,
                                          "side": c["side"], "weight": c["weight"]}
                                      for d, c in dims.items()}}
                   for k in raw if k[1] in excluded}
        for members in cohorts:
            results.update(compute_two_sided_index({k: raw[k] for k in members}, p, sides))
        for (country, occ), res in results.items():
            res["components"] = {
                dim: {**c, "indicator": dims[dim]["indicator"], "scope": dims[dim]["scope"],
                      "measure": dims[dim]["measure"], "detail": detail[(country, occ)][dim]}
                for dim, c in res["components"].items()
            }
            yield country, occ, year, res


def recompute_moctezuma(session: Session, method: Methodology) -> int:
    """Recalculate every reference year. Returns the number of scores stored."""
    now = datetime.now(UTC)
    session.execute(delete(MoctezumaScore).where(
        MoctezumaScore.methodology_id == method.methodology_id))
    stored = 0
    for country, occ, year, res in two_sided_results(session, "moctezuma", SIDES):
        session.add(MoctezumaScore(
            country_iso3=country, occupation_code=occ, year=year, score=res["score"],
            level=res["level"], pace=res["pace"], readiness=res["readiness"],
            gap=res["gap"], pace_coverage=res["coverage"]["pace"],
            readiness_coverage=res["coverage"]["readiness"], components=res["components"],
            methodology_id=method.methodology_id, computed_at=now,
        ))
        stored += 1
    return stored
