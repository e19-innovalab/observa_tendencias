"""Moctezuma indicator: asymmetry between the technological pace an occupation faces and the
capacity to respond to it. Scores are relative to the comparison cohort.

Dimensions, sides, weights and levels come from config/analytics.yaml (section moctezuma)."""

from app.analytics.employability import level_for, min_max_scale
from app.core.config_files import analytics_params

SIDES = ("pace", "readiness")


def side_score(scaled: dict[str, float | None], dims: dict) -> tuple[float | None, float]:
    """Weighted mean of a side's scaled dimensions with data, and the share of its weight they cover."""
    total = sum(d["weight"] for d in dims.values())
    avail = {k: d["weight"] for k, d in dims.items() if scaled.get(k) is not None}
    if not avail:
        return None, 0.0
    w = sum(avail.values())
    return sum(scaled[k] * wk for k, wk in avail.items()) / w, w / total


def compute_two_sided_index(cohort: dict, p: dict, sides: tuple[str, str]) -> dict:
    """Index of a side that pushes the score up against one that holds it back (e.g. pace of
    change vs capacity to respond). cohort: {key: {dimension: raw_value | None}}; p: the
    section's parameters; sides: (push, counter) as named in the dimensions' `side`.

    score = (w_push · push + w_counter · (100 − counter)) / (w_push + w_counter), so 50 means both
    sides are even. Returns {key: {score, level, <push>, <counter>, gap, coverage, components}}.
    Below min_side_coverage on either side the level is 'insufficient_data' and score is None.
    """
    push, counter = sides
    dims = p["dimensions"]
    top = p["scale_max"]
    scaled = {
        d: min_max_scale({k: vals.get(d) for k, vals in cohort.items()},
                         conf["higher_is_more"], p)
        for d, conf in dims.items()
    }
    by_side = {s: {d: c for d, c in dims.items() if c["side"] == s} for s in sides}
    results = {}
    for key, vals in cohort.items():
        own = {d: scaled[d][key] for d in dims}
        values = {s: side_score(own, by_side[s]) for s in sides}
        components = {
            d: {"raw": vals.get(d), "normalized": own[d], "side": c["side"],
                "weight": c["weight"]}
            for d, c in dims.items()
        }
        (up, up_cov), (down, down_cov) = values[push], values[counter]
        coverage = {push: up_cov, counter: down_cov}
        if min(up_cov, down_cov) < p["min_side_coverage"]:
            results[key] = {"score": None, "level": "insufficient_data", push: up,
                            counter: down, "gap": None, "coverage": coverage,
                            "components": components}
            continue
        w = p["side_weights"]
        score = (w[push] * up + w[counter] * (top - down)) / (w[push] + w[counter])
        results[key] = {"score": score, "level": level_for(score, p["levels"]), push: up,
                        counter: down, "gap": up - down, "coverage": coverage,
                        "components": components}
    return results


def compute_moctezuma_index(cohort: dict, params: dict | None = None) -> dict:
    """Pace of change (pushes) against capacity to respond (holds back)."""
    return compute_two_sided_index(cohort, analytics_params("moctezuma", params), SIDES)
