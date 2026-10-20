"""Short-horizon projections with Holt exponential smoothing (plan 8.3)."""
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.core.config_files import analytics_params


def project_series(values: list[float], params: dict | None = None) -> list[dict] | None:
    """Return [{step, value, lower_bound, upper_bound}] or None if history is insufficient.

    The caller stores these with data_type='projected' and flags them as indicative.
    """
    p = analytics_params("projections", params)
    if len(values) < p["min_points"]:
        return None
    y = np.asarray(values, dtype=float)
    fit = ExponentialSmoothing(y, trend="add", initialization_method="estimated").fit()
    forecast = fit.forecast(p["horizon"])
    sigma = float(np.std(y - fit.fittedvalues, ddof=1))
    out = []
    for step, value in enumerate(forecast, start=1):
        margin = p["ci_z"] * sigma * np.sqrt(step)
        out.append(
            {
                "step": step,
                "value": float(value),
                "lower_bound": float(value - margin),
                "upper_bound": float(value + margin),
            }
        )
    return out
