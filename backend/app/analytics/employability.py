"""Employability index (plan 8.1). Scores are relative to the comparison cohort."""

DEFAULT_PARAMS = {
    "weights": {
        "demand": 0.30, "wages": 0.25, "stability": 0.20, "outlook": 0.15, "skills_fit": 0.10,
    },
    "higher_is_better": {
        "demand": True, "wages": True, "stability": False, "outlook": True, "skills_fit": True,
    },
    "levels": {"low": 40, "high": 70},
    "min_coverage": 0.6,
}


def min_max_scale(
    values: dict[str, float | None], higher_is_better: bool = True
) -> dict[str, float | None]:
    """Scale each entity's value to 0-100 within the cohort, inverting when lower is better."""
    present = {k: v for k, v in values.items() if v is not None}
    if not present:
        return dict.fromkeys(values)
    lo, hi = min(present.values()), max(present.values())
    out: dict[str, float | None] = {}
    for k, v in values.items():
        if v is None:
            out[k] = None
        elif hi == lo:
            out[k] = 50.0
        else:
            s = (v - lo) / (hi - lo) * 100
            out[k] = s if higher_is_better else 100 - s
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
    p = {**DEFAULT_PARAMS, **(params or {})}
    weights = p["weights"]
    dims = list(weights)
    scaled = {
        d: min_max_scale(
            {occ: vals.get(d) for occ, vals in cohort.items()}, p["higher_is_better"].get(d, True)
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
