"""Skill gaps: demand growth vs training (supply) growth per skill and country (plan 8.4).

Demand of an occupation: growth of its employment (same measure as the ISE's net demand).
Supply of an occupation: growth of the graduates of the careers that train for it, through a
career -> ISCO crosswalk (config/reference). A skill's demand and supply are the averages over
the occupations that use it, weighted by the skill's ESCO weight. Parameters:
config/analytics.yaml -> skill_gaps.
"""
from collections import defaultdict
from datetime import UTC, datetime

import yaml
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics.employability_run import Point, _load_points, dimension_value
from app.core.config import settings
from app.core.config_files import analytics_params, catalog
from app.datasets.profiles import normalize_text
from app.models import Graduate, Methodology, OccupationSkill, SkillGap

DEMAND_INDICATOR = "employment"
TOP_OCCUPATIONS_IN_DETAILS = 5


def _growth_conf(p: dict, min_base: float) -> dict:
    return {"measure": "growth", "window_years": p["window_years"],
            "exclude_years": p["exclude_years"], "min_base": min_base}


def supply_growth_conf(p: dict) -> dict:
    return {"measure": "growth", "window_years": p["supply_window_years"],
            "exclude_years": p["supply_exclude_years"], "min_base": p["min_supply_base"]}


def load_crosswalk(path: str) -> dict:
    with (settings.config_dir / path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


ANY_LEVEL = "*"


def crosswalk_levels(crosswalk: dict) -> list[str]:
    """Levels a crosswalk covers: `levels` (list) or, in older files, `level`."""
    return crosswalk.get("levels") or [crosswalk["level"]]


def crosswalk_codes(entry, level: str) -> list[str]:
    """ISCO codes of a crosswalk row for a level. A row is a list (same codes for every level)
    or a mapping {level: [codes], "*": [codes for the other levels]}."""
    if isinstance(entry, dict):
        entry = entry.get(level, entry.get(ANY_LEVEL, []))
    return [f"{c:04d}" if isinstance(c, int) else str(c).zfill(4) for c in entry or []]


def occupation_supply(session: Session, country: str, crosswalk: dict) -> dict[str, dict[int, float]]:
    """{occupation: {year: graduates}}: each career's graduates split equally among its codes."""
    careers = {normalize_text(k): v for k, v in crosswalk["careers"].items()}
    out: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    rows = session.scalars(select(Graduate).where(
        Graduate.country_iso3 == country, Graduate.level.in_(crosswalk_levels(crosswalk)))).all()
    for g in rows:
        codes = crosswalk_codes(careers.get(g.career_key), g.level)
        for code in codes:
            out[code][g.year] += g.graduates / len(codes)
    return out


def recompute_skill_gaps(session: Session, method: Methodology) -> int:
    p = analytics_params("skill_gaps")
    ise = analytics_params("employability")
    demand_conf = _growth_conf(p, ise["dimensions"]["net_demand"].get("min_base", 0))
    supply_conf = supply_growth_conf(p)
    max_age = ise["max_age_years"]

    demand_points = _load_points(session, {DEMAND_INDICATOR})
    countries = [c.iso3 for c in catalog().countries]
    reference = countries[0]  # ESCO relations are the same for every country
    skills_by_occ: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for occ, skill, weight in session.execute(select(
            OccupationSkill.occupation_code, OccupationSkill.skill_code, OccupationSkill.weight)
            .where(OccupationSkill.country_iso3 == reference)).all():
        skills_by_occ[occ].append((skill, float(weight)))
    if not skills_by_occ:
        return 0

    session.execute(delete(SkillGap).where(SkillGap.methodology_id == method.methodology_id))
    now, stored = datetime.now(UTC), 0
    for country in countries:
        crosswalk_path = p["crosswalks"].get(country)
        supply_series = occupation_supply(session, country, load_crosswalk(crosswalk_path)) \
            if crosswalk_path else {}
        demand_years = [pt.year for (ind, c, _), pts in demand_points.items() if c == country
                        for pt in pts]
        supply_years = [y for series in supply_series.values() for y in series]
        if not demand_years:
            continue
        year = min(max(demand_years), max(supply_years)) if supply_years else max(demand_years)

        demand, supply = {}, {}
        for occ in skills_by_occ:
            d, _ = dimension_value(demand_points.get((DEMAND_INDICATOR, country, occ), []),
                                   demand_conf, year, max_age)
            if d is not None:
                demand[occ] = d
            series = supply_series.get(occ)
            if series:
                pts = [Point(y, v, "graduates", None) for y, v in sorted(series.items())]
                s, _ = dimension_value(pts, supply_conf, year, max_age)
                if s is not None:
                    supply[occ] = s

        per_skill: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for occ, pairs in skills_by_occ.items():
            for skill, weight in pairs:
                per_skill[skill].append((occ, weight))
        for skill, occs in per_skill.items():
            total = sum(w for _, w in occs)
            d_w = sum(w for o, w in occs if o in demand)
            s_w = sum(w for o, w in occs if o in supply)
            d = sum(w * demand[o] for o, w in occs if o in demand) / d_w if d_w else None
            s = sum(w * supply[o] for o, w in occs if o in supply) / s_w if s_w else None
            d_cov, s_cov = (d_w / total, s_w / total) if total else (0.0, 0.0)
            full = d is not None and s is not None and s_cov >= p["min_supply_coverage"]
            sufficiency = "full" if full else ("partial" if d is not None or s is not None
                                               else "none")
            top = sorted(occs, key=lambda ow: -ow[1])[:TOP_OCCUPATIONS_IN_DETAILS]
            session.add(SkillGap(
                country_iso3=country, skill_code=skill, year=year, demand_growth=d,
                supply_growth=s, gap=(d - s) if full else None,
                is_emerging=d is not None and d > p["emerging_growth"],
                data_sufficiency=sufficiency, demand_coverage=d_cov, supply_coverage=s_cov,
                occupations=len(occs),
                details={"top_occupations": [
                    {"occupation": o, "weight": w, "demand": demand.get(o), "supply": supply.get(o)}
                    for o, w in top]},
                methodology_id=method.methodology_id, computed_at=now,
            ))
            stored += 1
    return stored
