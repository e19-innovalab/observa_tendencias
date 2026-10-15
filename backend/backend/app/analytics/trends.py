"""Trend analysis (plan 8.2). Pure functions: parameters come from the active methodology."""
import numpy as np

DEFAULT_PARAMS = {"threshold": 0.02, "min_points": 4}


def compute_growth(values: list[float]) -> float | None:
    """Percent change between first and last point of the window (fraction, 0.05 = 5%)."""
    if len(values) < 2 or values[0] == 0:
        return None
    return (values[-1] - values[0]) / abs(values[0])


def compute_slope(values: list[float]) -> float | None:
    """Slope of a linear regression over the window, normalized by the mean level."""
    if len(values) < 2:
        return None
    mean = float(np.mean(values))
    if mean == 0:
        return None
    slope = np.polyfit(np.arange(len(values)), values, 1)[0]
    return float(slope / abs(mean))


def classify_trend(values: list[float], params: dict | None = None) -> dict:
    """Return slope, pct_change and trend_state (growing / stable / declining / insufficient_data)."""
    p = {**DEFAULT_PARAMS, **(params or {})}
    if len(values) < p["min_points"]:
        return {"slope": None, "pct_change": None, "trend_state": "insufficient_data"}
    slope, pct = compute_slope(values), compute_growth(values)
    if slope is None:
        return {"slope": None, "pct_change": pct, "trend_state": "insufficient_data"}
    if slope > p["threshold"]:
        state = "growing"
    elif slope < -p["threshold"]:
        state = "declining"
    else:
        state = "stable"
    return {"slope": slope, "pct_change": pct, "trend_state": state}
