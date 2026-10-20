"""Employability index (plan 8.1, mockup ISE). Scores are relative to the comparison cohort.

Dimensions, weights and levels come from config/analytics.yaml (section employability)."""

from app.core.config_files import analytics_params


def min_max_scale(
    values: dict[str, float | None],
    higher_is_better: bool = True,
    params: dict | None = None,
) -> dict[str, float | None]:
    """Scale each entity's value to 0-scale_max within the cohort, inverting when lower is better."""
    p = analytics_params("employability", params)
    top = p["scale_max"]
    present = {k: v for k, v in values.items() if v is not None}
    if not present:
        return dict.fromkeys(values)
    lo, hi = min(present.values()), max(present.values())
    out: dict[str, float | None] = {}
    for k, v in values.items():
        if v is None:
            out[k] = None
        elif hi == lo:
            out[k] = p["flat_cohort_score"]
        else:
            s = (v - lo) / (hi - lo) * top
            out[k] = s if higher_is_better else top - s
    return out


def level_for(score: float, levels: dict) -> str:
    if score < levels["low"]:
        return "low"
    if score > levels["high"]:
        return "high"
    return "medium"


def compute_employability_index(
    cohort: dict[str, dict[str, float | None]], params: dict | None = None
) -> dict[str, dict]:
    """cohort: {occupation_code: {dimension: raw_value | None}}.

    Returns {occupation_code: {score, level, coverage_ratio, components}}.
    Missing dimensions have their weight redistributed; below min_coverage the level is
    'insufficient_data' and score is None.
    """
    p = analytics_params("employability", params)
    weights = p["weights"]
    dims = list(weights)
    scaled = {
        d: min_max_scale(
            {occ: vals.get(d) for occ, vals in cohort.items()}, p["higher_is_better"].get(d, True), p
        )
        for d in dims
    }
    results = {}
    for occ, vals in cohort.items():
        avail = [d for d in dims if scaled[d][occ] is not None]
        coverage = sum(weights[d] for d in avail) / sum(weights.values())
        components = {
            d: {"raw": vals.get(d), "normalized": scaled[d][occ], "weight": weights[d]}
            for d in dims
        }
        if not avail or coverage < p["min_coverage"]:
            results[occ] = {
                "score": None,
                "level": "insufficient_data",
                "coverage_ratio": coverage,
                "components": components,
            }
            continue
        total_w = sum(weights[d] for d in avail)
        score = sum(scaled[d][occ] * weights[d] for d in avail) / total_w
        results[occ] = {
            "score": score,
            "level": level_for(score, p["levels"]),
            "coverage_ratio": coverage,
            "components": components,
        }
    return results
