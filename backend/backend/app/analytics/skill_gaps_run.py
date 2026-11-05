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

from app.analytics.employability_run import _load_points, dimension_value
from app.core.config import settings
from app.core.config_files import analytics_params, catalog
from app.datasets.profiles import normalize_text, profiles
from app.models import (
    Graduate,
    Methodology,
    OccupationSkill,
    Skill,
    SkillGap,
    SkillGroupGap,
    Source,
)

DEMAND_INDICATOR = "employment"
TOP_OCCUPATIONS_IN_DETAILS = 5
TOP_SKILLS_IN_DETAILS = 8


def _growth_conf(p: dict, min_base: float) -> dict:
    return {"measure": "growth", "window_years": p["window_years"],
            "exclude_years": p["exclude_years"], "min_base": min_base}


def supply_growth_conf(p: dict) -> dict:
    return {"measure": "growth", "window_years": p["supply_window_years"],
            "exclude_years": p["supply_exclude_years"], "min_base": p["min_supply_base"],
            "smoothing_years": p["supply_smoothing_years"], "max_jump": p["supply_max_jump"]}


def supply_growth(series: dict[int, float], year: int, conf: dict, max_age: int
                  ) -> tuple[float | None, bool]:
    """(average annual growth of graduates as of `year`, unstable?). Compares the average of the
    first `smoothing_years` of the window with the average of the last ones; a series that jumps
    more than `max_jump` times from one year to the next inside the window is unstable (None)."""
    excluded = set(conf.get("exclude_years", []))
    years = sorted(y for y in series if year - max_age <= y <= year and y not in excluded)
    if not years:
        return None, False
    last, window, k = years[-1], conf["window_years"], conf["smoothing_years"]
    base = last - window
    start = [y for y in years if base - k < y <= base]
    end = [y for y in years if last - k < y <= last]
    if not start:
        return None, False
    span = [y for y in years if base - k < y <= last]
    for a, b in zip(span, span[1:]):
        low, high = sorted((series[a], series[b]))
        if (low > 0 and high / low > conf["max_jump"]) or (low <= 0 < high and high >= conf["min_base"]):
            return None, True
    start_avg = sum(series[y] for y in start) / len(start)
    end_avg = sum(series[y] for y in end) / len(end)
    if start_avg <= 0 or start_avg < conf["min_base"]:
        return None, False
    return (end_avg / start_avg) ** (1 / window) - 1, False


def _read_yaml(path: str) -> dict:
    with (settings.config_dir / path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_crosswalk(path: str) -> dict:
    """A career -> CIUO crosswalk. Files with `via` give each career a CINE-F 2013 field instead
    of occupations; they are expanded here through the shared field -> CIUO table, so the rest of
    the code sees the usual {career: {level: [codes]}} structure."""
    cw = _read_yaml(path)
    return expand_cine_crosswalk(cw) if cw.get("via") else cw


TECHNICAL = "tecnico"
DEFAULT_CODES = "*"


def field_codes(field, technical: bool) -> list:
    """CIUO codes of a CINE-F field: a list, or {"*": [...], "tecnico": [...]}."""
    if not isinstance(field, dict):
        return field or []
    return field.get(TECHNICAL, field.get(DEFAULT_CODES, [])) if technical \
        else field.get(DEFAULT_CODES, [])


def expand_cine_crosswalk(cw: dict) -> dict:
    """careers: {name: {cine, tecnico}} -> {name: {level: [codes]}}; keeps each career's field in
    "cine" for the review view. A career is technical by name (tecnico) or by its level
    (technical_levels, e.g. Argentina's Pregrado)."""
    table = _read_yaml(cw["via"])
    fields = table["fields"]
    names = _read_yaml(table["classification"])["detailed"] if table.get("classification") else {}
    levels = crosswalk_levels(cw)
    technical_levels = set(cw.get("technical_levels") or [])
    careers, cine = {}, {}
    for name, entry in cw["careers"].items():
        code = (entry or {}).get("cine")
        if code is not None and code not in fields:
            raise ValueError(f"{name}: CINE-F field {code} is not in {cw['via']}")
        named_technical = bool((entry or {}).get(TECHNICAL))
        cine[name] = {"code": code, "name": names.get(code), "technical": named_technical}
        careers[name] = {level: field_codes(fields.get(code), named_technical
                                            or level in technical_levels) if code else []
                         for level in levels}
    return {**cw, "careers": careers, "cine": cine,
            "reviewed": bool(cw.get("reviewed")) and bool(table.get("reviewed"))}


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


def occupation_supply(session: Session, country: str, crosswalk: dict,
                      supplement: dict | None = None) -> dict[str, dict[int, float]]:
    """{occupation: {year: graduates}}: each career's graduates split equally among its codes.
    Graduates come from the crosswalk's own source; a supplement (skill_gaps.supply_supplements)
    only adds the years that source does not have, with its combined level split into the
    crosswalk's levels by each career's latest shares in the main source."""
    careers = {normalize_text(k): v for k, v in crosswalk["careers"].items()}
    levels = crosswalk_levels(crosswalk)
    main_source = _profile_source_id(session, crosswalk.get("source_profile"))
    stmt = select(Graduate).where(Graduate.country_iso3 == country, Graduate.level.in_(levels))
    if main_source is not None:
        stmt = stmt.where(Graduate.source_id == main_source)
    rows = [(g.career_key, g.level, g.year, g.graduates) for g in session.scalars(stmt).all()]
    if supplement:
        rows += _supplement_rows(session, country, supplement, levels, rows)
    out: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for career_key, level, year, graduates in rows:
        codes = crosswalk_codes(careers.get(career_key), level)
        for code in codes:
            out[code][year] += graduates / len(codes)
    return out


def _profile_source_id(session: Session, profile_code: str | None) -> int | None:
    if not profile_code or profile_code not in profiles():
        return None
    return session.scalar(select(Source.source_id).where(
        Source.source_code == profiles()[profile_code].source))


def _supplement_rows(session: Session, country: str, supplement: dict, levels: list[str],
                     main: list[tuple]) -> list[tuple]:
    """Rows of the supplement for the years the main source lacks, split by level."""
    source_id = _profile_source_id(session, supplement["profile"])
    if source_id is None:
        return []
    main_years = {year for _, _, year, _ in main}
    shares: dict[str, dict[str, float]] = {}  # career -> level -> share, latest year with data
    by_career: dict[str, dict[int, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for career_key, level, year, graduates in main:
        by_career[career_key][year][level] = by_career[career_key][year].get(level, 0) + graduates
    for career_key, years in by_career.items():
        for year in sorted(years, reverse=True):
            total = sum(years[year].values())
            if total > 0:
                shares[career_key] = {lv: v / total for lv, v in years[year].items()}
                break
    out = []
    for g in session.scalars(select(Graduate).where(
            Graduate.country_iso3 == country, Graduate.source_id == source_id,
            Graduate.level == supplement["combined_level"])).all():
        if g.year in main_years:
            continue
        for level, share in shares.get(g.career_key, {}).items():
            if level in levels and share:
                out.append((g.career_key, level, g.year, g.graduates * share))
    return out


def _gap_values(occs: list[tuple[str, float]], demand: dict, supply: dict, p: dict) -> dict:
    """Weighted demand and supply growth over the occupations that use a skill (or a group)."""
    total = sum(w for _, w in occs)
    d_w = sum(w for o, w in occs if o in demand)
    s_w = sum(w for o, w in occs if o in supply)
    d = sum(w * demand[o] for o, w in occs if o in demand) / d_w if d_w else None
    s = sum(w * supply[o] for o, w in occs if o in supply) / s_w if s_w else None
    d_cov, s_cov = (d_w / total, s_w / total) if total else (0.0, 0.0)
    full = d is not None and s is not None and s_cov >= p["min_supply_coverage"]
    sufficiency = "full" if full else ("partial" if d is not None or s is not None else "none")
    top = sorted(occs, key=lambda ow: -ow[1])[:TOP_OCCUPATIONS_IN_DETAILS]
    return dict(
        demand_growth=d, supply_growth=s, gap=(d - s) if full else None,
        is_emerging=d is not None and d > p["emerging_growth"], data_sufficiency=sufficiency,
        demand_coverage=d_cov, supply_coverage=s_cov, occupations=len(occs),
        top_occupations=[{"occupation": o, "weight": w, "demand": demand.get(o), "supply": supply.get(o)}
                         for o, w in top])


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

    per_skill: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for occ, pairs in skills_by_occ.items():
        for skill, weight in pairs:
            per_skill[skill].append((occ, weight))
    # ESCO groups: an occupation weighs as its strongest skill of the group (near-identical skills
    # of a group are not added up); member skills ranked by total weight for the details
    group_of = dict(session.execute(select(Skill.skill_code, Skill.group_code)
                                    .where(Skill.group_code.is_not(None))).all())
    group_weight: dict[str, dict[str, float]] = defaultdict(dict)
    group_skills: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for occ, pairs in skills_by_occ.items():
        for skill, weight in pairs:
            group = group_of.get(skill)
            if group:
                group_weight[group][occ] = max(group_weight[group].get(occ, 0.0), weight)
                group_skills[group][skill] += weight
    per_group = {g: list(occs.items()) for g, occs in group_weight.items()}

    session.execute(delete(SkillGap).where(SkillGap.methodology_id == method.methodology_id))
    session.execute(delete(SkillGroupGap).where(SkillGroupGap.methodology_id == method.methodology_id))
    now, stored = datetime.now(UTC), 0
    for country in countries:
        crosswalk_path = p["crosswalks"].get(country)
        supply_series = occupation_supply(session, country, load_crosswalk(crosswalk_path),
                                          p.get("supply_supplements", {}).get(country)) \
            if crosswalk_path else {}
        demand_years = [pt.year for (ind, c, _), pts in demand_points.items() if c == country
                        for pt in pts]
        supply_years = [y for series in supply_series.values() for y in series]
        if not demand_years:
            continue
        latest = min(max(demand_years), max(supply_years)) if supply_years else max(demand_years)
        for year in range(latest - p["history_years"] + 1, latest + 1):
            stored += _store_year(session, method, now, p, country, year, skills_by_occ, per_skill,
                                  per_group, group_skills, demand_points, supply_series,
                                  demand_conf, supply_conf, max_age)
    return stored


def _store_year(session, method, now, p, country, year, skills_by_occ, per_skill, per_group,
                group_skills, demand_points, supply_series, demand_conf, supply_conf, max_age) -> int:
    """Gaps of one country and reference year (skills and ESCO groups), with the data up to it."""
    demand, supply, unstable = {}, {}, set()
    for occ in skills_by_occ:
        d, _ = dimension_value(demand_points.get((DEMAND_INDICATOR, country, occ), []),
                               demand_conf, year, max_age)
        if d is not None:
            demand[occ] = d
        series = supply_series.get(occ)
        if series:
            s, jumpy = supply_growth(series, year, supply_conf, max_age)
            if s is not None:
                supply[occ] = s
            elif jumpy:
                unstable.add(occ)
    if not demand and not supply:
        return 0
    stored = 0
    for skill, occs in per_skill.items():
        v = _gap_values(occs, demand, supply, p)
        top = v.pop("top_occupations")
        session.add(SkillGap(country_iso3=country, skill_code=skill, year=year, **v,
                             details={"top_occupations": top,
                                      "unstable_supply": sorted(o for o, _ in occs if o in unstable)},
                             methodology_id=method.methodology_id, computed_at=now))
        stored += 1
    for group, occs in per_group.items():
        v = _gap_values(occs, demand, supply, p)
        top = v.pop("top_occupations")
        members = sorted(group_skills[group].items(), key=lambda sw: -sw[1])
        session.add(SkillGroupGap(
            country_iso3=country, group_code=group, year=year, **v, skills=len(members),
            details={"top_occupations": top,
                     "top_skills": [sk for sk, _ in members[:TOP_SKILLS_IN_DETAILS]],
                     "unstable_supply": sorted(o for o, _ in occs if o in unstable)},
            methodology_id=method.methodology_id, computed_at=now))
    return stored
