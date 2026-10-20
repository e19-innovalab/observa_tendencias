"""Alert rules (plan 8.5). Each rule returns an alert dict or None; persistence is the caller's job.

Thresholds, severities and message templates come from config/analytics.yaml (section alerts).
"""
from datetime import datetime, timedelta, timezone

import numpy as np

from app.core.config_files import analytics_params


def significant_change(series: list[float], params: dict | None = None,
                       absolute: bool = False) -> dict | None:
    """Flag a latest-period change above the threshold or beyond z_threshold of past changes.

    Relative mode (counts, money, indexes): change as a ratio vs change_pct, skipped when the
    previous value is under min_base. Absolute mode (percent units): change in points vs
    absolute_change.
    """
    p = analytics_params("alerts", params)
    if len(series) < 2:
        return None
    prev, cur = series[-2], series[-1]
    if absolute:
        change, threshold = cur - prev, p["absolute_change"]
    else:
        if prev == 0 or abs(prev) < p["min_base"]:
            return None
        change, threshold = (cur - prev) / abs(prev), p["change_pct"]
    triggered = abs(change) > threshold
    if len(series) >= p["z_min_points"]:
        diffs = np.diff(series[:-1])
        sd = float(np.std(diffs, ddof=1))
        if sd > 0 and abs((cur - prev) - float(np.mean(diffs))) / sd > p["z_threshold"]:
            triggered = True
    if not triggered:
        return None
    high = abs(change) > p["high_severity_factor"] * threshold
    sev = p["severities"]
    template = "significant_change_points" if absolute else "significant_change"
    return {
        "alert_type": "significant_change",
        "severity": sev["significant_change_high"] if high else sev["significant_change_default"],
        "previous_value": prev,
        "current_value": cur,
        "message": p["messages"][template].format(change=change),
    }


def _changed(previous: str | None, current: str | None) -> bool:
    return bool(
        previous and current and previous != current
        and "insufficient_data" not in (previous, current)
    )


def _state_change(alert_type: str, previous: str | None, current: str | None,
                  params: dict | None) -> dict | None:
    if not _changed(previous, current):
        return None
    p = analytics_params("alerts", params)
    return {
        "alert_type": alert_type,
        "severity": p["severities"][alert_type],
        "message": p["messages"][alert_type].format(previous=previous, current=current),
    }


def index_level_change(previous: str | None, current: str | None,
                       params: dict | None = None) -> dict | None:
    return _state_change("index_level_change", previous, current, params)


def trend_reversal(previous: str | None, current: str | None,
                   params: dict | None = None) -> dict | None:
    return _state_change("trend_reversal", previous, current, params)


def new_skill_gap(
    previous_gap: float | None, current_gap: float | None, params: dict | None = None
) -> dict | None:
    p = analytics_params("alerts", params)
    if current_gap is None or current_gap <= p["gap_threshold"]:
        return None
    if previous_gap is not None and previous_gap > p["gap_threshold"]:
        return None
    return {
        "alert_type": "new_skill_gap",
        "severity": p["severities"]["new_skill_gap"],
        "previous_value": previous_gap,
        "current_value": current_gap,
        "message": p["messages"]["new_skill_gap"],
    }


def stale_source(
    last_update: datetime,
    expected_days: float,
    now: datetime | None = None,
    params: dict | None = None,
) -> dict | None:
    p = analytics_params("alerts", params)
    now = now or datetime.now(timezone.utc)
    if now - last_update <= timedelta(days=expected_days * p["stale_factor"]):
        return None
    return {
        "alert_type": "stale_source",
        "severity": p["severities"]["stale_source"],
        "message": p["messages"]["stale_source"].format(last_update=last_update),
    }


def evaluate_alert_rules(entity: dict, params: dict | None = None) -> list[dict]:
    """entity may hold: series, level/prev_level, trend/prev_trend, gap/prev_gap,
    last_update/expected_days. Only rules whose inputs are present are evaluated."""
    found = []
    if "series" in entity:
        found.append(significant_change(entity["series"], params))
    if "level" in entity:
        found.append(index_level_change(entity.get("prev_level"), entity["level"], params))
    if "trend" in entity:
        found.append(trend_reversal(entity.get("prev_trend"), entity["trend"], params))
    if "gap" in entity:
        found.append(new_skill_gap(entity.get("prev_gap"), entity["gap"], params))
    if "last_update" in entity:
        found.append(stale_source(entity["last_update"], entity["expected_days"], params=params))
    return [a for a in found if a]
