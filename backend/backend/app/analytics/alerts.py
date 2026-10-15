"""Alert rules (plan 8.5). Each rule returns an alert dict or None; persistence is the caller's job."""
from datetime import datetime, timedelta, timezone

import numpy as np

DEFAULT_PARAMS = {
    "change_pct": 0.10,
    "z_threshold": 2.0,
    "gap_threshold": 20.0,
    "stale_factor": 1.5,
    "min_base": 30,  # ignore changes whose previous value is below this (tiny bases blow up %)
}


def significant_change(series: list[float], params: dict | None = None) -> dict | None:
    """Flag a latest-period change above change_pct or beyond z_threshold of past changes.

    Skipped when the previous value is under min_base: percent changes on tiny bases are noise.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    if len(series) < 2 or series[-2] == 0:
        return None
    prev, cur = series[-2], series[-1]
    if abs(prev) < p["min_base"]:
        return None
    change = (cur - prev) / abs(prev)
    triggered = abs(change) > p["change_pct"]
    if len(series) >= 5:
        diffs = np.diff(series[:-1])
        sd = float(np.std(diffs, ddof=1))
        if sd > 0 and abs((cur - prev) - float(np.mean(diffs))) / sd > p["z_threshold"]:
            triggered = True
    if not triggered:
        return None
    return {
        "alert_type": "significant_change",
        "severity": "high" if abs(change) > 2 * p["change_pct"] else "medium",
        "previous_value": prev,
        "current_value": cur,
        "message": f"Variación de {change:+.1%} respecto del período anterior",
    }


def _changed(previous: str | None, current: str | None) -> bool:
    return bool(
        previous and current and previous != current
        and "insufficient_data" not in (previous, current)
    )


def index_level_change(previous: str | None, current: str | None) -> dict | None:
    if not _changed(previous, current):
        return None
    return {
        "alert_type": "index_level_change",
        "severity": "medium",
        "message": f"El nivel de empleabilidad pasó de {previous} a {current}",
    }


def trend_reversal(previous: str | None, current: str | None) -> dict | None:
    if not _changed(previous, current):
        return None
    return {
        "alert_type": "trend_reversal",
        "severity": "medium",
        "message": f"La tendencia cambió de {previous} a {current}",
    }


def new_skill_gap(
    previous_gap: float | None, current_gap: float | None, params: dict | None = None
) -> dict | None:
    p = {**DEFAULT_PARAMS, **(params or {})}
    if current_gap is None or current_gap <= p["gap_threshold"]:
        return None
    if previous_gap is not None and previous_gap > p["gap_threshold"]:
        return None
    return {
        "alert_type": "new_skill_gap",
        "severity": "medium",
        "previous_value": previous_gap,
        "current_value": current_gap,
        "message": "La brecha de habilidad superó el umbral por primera vez",
    }


def stale_source(
    last_update: datetime,
    expected_days: float,
    now: datetime | None = None,
    params: dict | None = None,
) -> dict | None:
    p = {**DEFAULT_PARAMS, **(params or {})}
    now = now or datetime.now(timezone.utc)
    if now - last_update <= timedelta(days=expected_days * p["stale_factor"]):
        return None
    return {
        "alert_type": "stale_source",
        "severity": "low",
        "message": f"Fuente sin actualizar desde {last_update:%Y-%m-%d}",
    }


def evaluate_alert_rules(entity: dict, params: dict | None = None) -> list[dict]:
    """entity may hold: series, level/prev_level, trend/prev_trend, gap/prev_gap,
    last_update/expected_days. Only rules whose inputs are present are evaluated."""
    found = []
    if "series" in entity:
        found.append(significant_change(entity["series"], params))
    if "level" in entity:
        found.append(index_level_change(entity.get("prev_level"), entity["level"]))
    if "trend" in entity:
        found.append(trend_reversal(entity.get("prev_trend"), entity["trend"]))
    if "gap" in entity:
        found.append(new_skill_gap(entity.get("prev_gap"), entity["gap"], params))
    if "last_update" in entity:
        found.append(stale_source(entity["last_update"], entity["expected_days"], params=params))
    return [a for a in found if a]
