"""Sísifo indicator: where studying more does not pay. Per ISCO-08 major group, country and year:
overeducation (the stone) against the group's earnings relative to those of the tertiary
educated (the reward), with the two-sided engine of the Moctezuma indicator. Computed on request
from the observations (a handful of groups per country); parameters in config/analytics.yaml
(section sisyphus). Also the country view: graduates working below their level and the wage
premium of tertiary education.
"""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.moctezuma import compute_two_sided_index
from app.core.config_files import analytics_params, education_requirements
from app.models import EducationMismatchCell, Observation

SECTION = "sisyphus"
Series = dict[int, float]


def input_indicators() -> set[str]:
    p = analytics_params(SECTION)
    dims = p["dimensions"].values()
    return ({d["indicator"] for d in dims} | {d["relative_to"] for d in dims if d.get("relative_to")}
            | set(p["display"].values()))


def not_applicable_groups(p: dict) -> set[str]:
    """Major groups whose required education is the highest band: they cannot be overeducated."""
    req = education_requirements(p["requirements_file"])
    top = req.bands[-1].code
    return {g for g, band in req.requirements.items() if band == top}


def latest(series: Series, year: int, max_age: int) -> tuple[float, int] | None:
    """Latest value up to `year`, at most max_age years older."""
    years = [y for y in series if y <= year and year - y <= max_age]
    return (series[max(years)], max(years)) if years else None


def load_series(session: Session, p: dict) -> tuple[dict, dict]:
    """(by_group, national): {indicator: {(country, group): {year: value}}} for the occupation
    series (each group counted once: its occupations share the value) and
    {indicator: {country: {year: value}}} for the national ones."""
    digits = p["group_digits"]
    codes = input_indicators()
    rows = session.execute(select(
        Observation.indicator_code, Observation.country_iso3, Observation.occupation_code,
        Observation.period_start, Observation.value,
    ).where(Observation.indicator_code.in_(codes), Observation.data_type == "observed",
            Observation.frequency == "A", Observation.sector_code.is_(None))).all()
    by_group: dict = defaultdict(lambda: defaultdict(dict))
    national: dict = defaultdict(lambda: defaultdict(dict))
    for ind, country, occ, start, value in rows:
        if occ is None:
            national[ind][country][start.year] = value
        else:
            by_group[ind][(country, occ[:digits])].setdefault(start.year, value)
    return by_group, national


def compute(session: Session, params: dict | None = None) -> dict[int, list[dict]]:
    """{year: [one row per country and group]} with the raw values, the index and the
    quadrant. Groups that cannot be overeducated are left out."""
    p = analytics_params(SECTION, params)
    dims, max_age = p["dimensions"], p["max_age_years"]
    by_group, national = load_series(session, p)
    skip = not_applicable_groups(p)
    keys = sorted({k for d in dims.values() for k in by_group[d["indicator"]]
                   if k[1] not in skip})
    years = sorted({y for d in dims.values() for s in by_group[d["indicator"]].values() for y in s})
    out: dict[int, list[dict]] = {}
    q = p["quadrants"]
    for year in [y for y in years if y >= p["first_year"]]:
        raw, detail = {}, {}
        for key in keys:
            raw[key], detail[key] = {}, {}
            for dim, c in dims.items():
                v = latest(by_group[c["indicator"]].get(key, {}), year, max_age)
                if v is not None and c.get("relative_to"):
                    den = latest(national[c["relative_to"]].get(key[0], {}), v[1], 0)
                    detail[key][dim] = {"year": v[1], "numerator": v[0],
                                        "denominator": den[0] if den else None}
                    v = (v[0] / den[0], v[1]) if den and den[0] else None
                elif v is not None:
                    detail[key][dim] = {"year": v[1]}
                raw[key][dim] = v[0] if v else None
        if not any(raw[k][d] is not None for k in keys for d in dims):
            continue
        results = compute_two_sided_index(raw, p, tuple(p["sides"]))
        rows = []
        for (country, group), res in results.items():
            over, ratio = raw[(country, group)]["overeducation"], raw[(country, group)]["earnings_vs_tertiary"]
            quadrant = None
            if over is not None and ratio is not None:
                high, low_pay = over >= q["overeducated_from"], ratio < q["paid_below"]
                quadrant = ("sisyphus" if low_pay else "overqualified_paid") if high \
                    else ("low_pay" if low_pay else "fits")
            usd = latest(by_group[p["display"]["group_earnings_usd"]].get((country, group), {}),
                         year, max_age)
            ppp = detail[(country, group)].get("earnings_vs_tertiary", {})
            rows.append({"country_iso3": country, "group_code": group, "year": year, **res,
                         "raw": raw[(country, group)], "detail": detail[(country, group)],
                         "quadrant": quadrant, "earnings_ppp": ppp.get("numerator"),
                         "earnings_usd": usd[0] if usd else None,
                         "tertiary_ppp": ppp.get("denominator")})
        out[year] = rows
    return out


def country_view(session: Session, countries: list[str], params: dict | None = None) -> dict:
    """{country: {year: {...}}}: share of the tertiary educated working in a group that does not
    require it (education mismatch cells), wage premium of tertiary over secondary education and
    the earnings behind it (USD and USD PPA)."""
    p = analytics_params(SECTION, params)
    req = education_requirements(p["requirements_file"])
    top = req.bands[-1].code
    _, national = load_series(session, p)
    d = p["display"]
    out: dict = defaultdict(dict)
    cells = session.scalars(select(EducationMismatchCell).where(
        EducationMismatchCell.country_iso3.in_(countries), EducationMismatchCell.band == top)).all()
    totals: dict = defaultdict(lambda: [0.0, 0.0])  # (country, year) -> [over, all with status]
    for c in cells:
        if c.status in ("over", "matched"):
            totals[(c.country_iso3, c.year)][1] += c.employed
            if c.status == "over":
                totals[(c.country_iso3, c.year)][0] += c.employed
    years = {y for (_, y) in totals} | {y for s in national[d["tertiary_ppp"]].values() for y in s}
    for country in countries:
        for year in sorted(years):
            over, base = totals.get((country, year), (0.0, 0.0))
            vals = {k: national[ind].get(country, {}).get(year) for k, ind in d.items()
                    if k != "group_earnings_usd"}
            premium = (vals["tertiary_ppp"] / vals["secondary_ppp"] - 1) \
                if vals["tertiary_ppp"] and vals["secondary_ppp"] else None
            if base or premium is not None:
                out[country][year] = {"graduates_below_share": over / base if base else None,
                                      "premium": premium, **vals}
    return out
