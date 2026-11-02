"""Reina Roja indicator: how much of an occupation's profile (technologies, skills) changes per
year between versions of a source. Pure functions; parameters in config/analytics.yaml
(section red_queen)."""
import math

from app.analytics.employability import level_for, min_max_scale
from app.core.config_files import analytics_params


def _contains(longer: str, shorter: str) -> bool:
    """`shorter` appears in `longer` as whole words."""
    return f" {shorter} " in f" {longer} "


def reconcile(before: set[str], after: set[str], min_chars: int) -> dict[str, str]:
    """Renamed items: {name in after: name in before}. A source may add or drop the vendor or a
    word between versions ("confluence" -> "atlassian confluence"); an item that left and one that
    entered count as the same when one name contains the other as whole words."""
    left, entered = before - after, after - before
    renamed: dict[str, str] = {}
    for new in sorted(entered):
        for old in sorted(left - set(renamed.values())):
            short, long_ = sorted((old, new), key=len)
            if len(short) >= min_chars and _contains(long_, short):
                renamed[new] = old
                break
    return renamed


def turnover(before: set[str], after: set[str]) -> float:
    """Jaccard distance: 1 - shared / in either (0 = same profile, 1 = nothing in common)."""
    union = before | after
    return 1 - len(before & after) / len(union) if union else 0.0


def annual_turnover(total: float, years: float) -> float:
    """Turnover per year: what stays, s = 1 - total, compounds as s^(1/years)."""
    return 1 - (1 - total) ** (1 / years) if years > 0 else total


def half_life(annual: float, cap: float) -> float:
    """Years until the profile shares only half with today's; cap when it barely changes."""
    if annual <= 0:
        return cap
    if annual >= 1:
        return 0.0
    return min(cap, math.log(0.5) / math.log(1 - annual))


def compute_red_queen_index(cohort: dict, params: dict | None = None) -> dict:
    """cohort: {occupation: {dimension: {"new_per_year", "annual"} | None}}.

    Returns {occupation: {score, level, turnover, half_life, coverage, normalized}}: each
    dimension's new items per year scaled 0-100 within the cohort, score = weighted mean of the
    dimensions with data (no data in any: insufficient_data). turnover is the weighted mean annual
    turnover and half_life follows from it."""
    p = analytics_params("red_queen", params)
    dims = p["dimensions"]
    scaled = {d: min_max_scale({k: (v.get(d) or {}).get("new_per_year") for k, v in cohort.items()},
                               True, p) for d in dims}
    total = sum(c["weight"] for c in dims.values())
    out = {}
    for key, vals in cohort.items():
        avail = {d: c["weight"] for d, c in dims.items() if vals.get(d) is not None}
        normalized = {d: scaled[d][key] for d in dims}
        if not avail:
            out[key] = {"score": None, "level": "insufficient_data", "turnover": None,
                        "half_life": None, "coverage": 0.0, "normalized": normalized}
            continue
        w = sum(avail.values())
        score = sum(normalized[d] * wd for d, wd in avail.items()) / w
        mean = sum(vals[d]["annual"] * wd for d, wd in avail.items()) / w
        out[key] = {"score": score, "level": level_for(score, p["levels"]), "turnover": mean,
                    "half_life": half_life(mean, p["half_life_cap"]), "coverage": w / total,
                    "normalized": normalized}
    return out
