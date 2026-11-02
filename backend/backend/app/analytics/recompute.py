"""Recalculate derived results after new data arrives (plan 10: recompute_affected).

For every observed series (indicator x country x sector x occupation) it stores:
- the trend state of the latest window in trend_results (history kept per window end);
- indicative projections in observations with data_type='projected';
- the employability index for every reference year, when one of its input indicators changed;
- the Moctezuma indicator (pace of change vs capacity to respond), likewise;
- the Ludita indicator (exposure to generative AI vs vitality), likewise;
- alerts for relevant changes (app/analytics/alerts_run.py).
Each result points to the methodologies row holding the exact parameters used.
"""
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics.alerts_run import evaluate_alerts
from app.analytics.employability_run import input_indicators, recompute_employability
from app.analytics.moctezuma_run import input_indicators as moctezuma_inputs
from app.analytics.projections import project_series
from app.analytics.recompute_keys import observed_series_keys
from app.analytics.trends import classify_trend
from app.core.config_files import IndicatorConf, analytics, analytics_params, catalog, indicators
from app.models import (
    EmployabilityScore,
    LuditaScore,
    Methodology,
    MoctezumaScore,
    Observation,
    SkillGap,
    SkillGroupGap,
    Source,
    TrendResult,
)
from app.normalization.periods import shift_period
from app.services.observations import query_points

# methodology_type -> section of config/analytics.yaml
METHODOLOGY_SECTIONS = {
    "trend": "trends",
    "projection": "projections",
    "employability_index": "employability",
    "skill_gap": "skill_gaps",
    "moctezuma_index": "moctezuma",
    "ludita_index": "ludita",
    "red_queen_index": "red_queen",
    "sisyphus_index": "sisyphus",
    "alert": "alerts",
}
DESCRIPTIVE_KEYS = ("name", "description", "version")


@dataclass
class RecomputeSummary:
    series: int = 0
    trends: int = 0
    projections: int = 0
    employability_scores: int = 0
    skill_gaps: int = 0
    moctezuma_scores: int = 0
    ludita_scores: int = 0
    red_queen_scores: int = 0
    alerts: int = 0


def methodology_params(methodology_type: str, overrides: dict | None = None) -> dict:
    return analytics_params(METHODOLOGY_SECTIONS[methodology_type], overrides)


def params_digest(methodology_type: str, overrides: dict | None = None) -> tuple[dict, dict, str]:
    """(full config section, calculation params, hash identifying version + params)."""
    full = methodology_params(methodology_type, overrides)
    params = {k: v for k, v in full.items() if k not in DESCRIPTIVE_KEYS}
    digest = hashlib.sha256(
        json.dumps({"version": full["version"], **params}, sort_keys=True).encode()
    ).hexdigest()
    return full, params, digest


def current_digests(methodology_type: str) -> set[str]:
    """Hashes of the parameter sets the current config produces (base + indicator overrides)."""
    overrides = [None]
    if methodology_type == "trend":
        overrides += [i.trend for i in indicators().indicators if i.trend]
    return {params_digest(methodology_type, o)[2] for o in overrides}


def ensure_methodology(
    session: Session, methodology_type: str, overrides: dict | None = None
) -> Methodology:
    """Get or create the methodologies row for the current parameters (+ per-indicator overrides)."""
    full, params, digest = params_digest(methodology_type, overrides)
    row = session.scalar(select(Methodology).where(
        Methodology.methodology_type == methodology_type, Methodology.params_hash == digest
    ))
    if row is None:
        row = Methodology(methodology_type=methodology_type, version=str(full["version"]),
                          params=params, params_hash=digest, name=full.get("name"),
                          description_md=full.get("description"), created_at=datetime.now(UTC))
        session.add(row)
        session.flush()
    else:  # name and description are not part of the identity: keep them current
        row.name, row.description_md = full.get("name"), full.get("description")
    return row


def _store_trend(session, ind: IndicatorConf, key: tuple, points, source_id: int,
                 method: Methodology, now: datetime) -> bool:
    """Store the trend of the latest window and of the window ending one period earlier, so a
    reversal can be detected from the data already available."""
    params = methodology_params("trend", ind.trend)
    stored = False
    for history in (points[:-1], points):
        window = history[-params["window_points"]:]
        if not window:
            continue
        result = classify_trend([p.value for p in window], params)
        _, country, sector, occupation, frequency = key
        row = dict(indicator_code=ind.code, country_iso3=country, sector_code=sector,
                   occupation_code=occupation, frequency=frequency,
                   window_end=window[-1].period_start, methodology_id=method.methodology_id)
        session.execute(delete(TrendResult).where(
            *(getattr(TrendResult, k).is_not_distinct_from(v) for k, v in row.items())
        ))
        session.add(TrendResult(**row, window_start=window[0].period_start, n_points=len(window),
                                slope=result["slope"], pct_change=result["pct_change"],
                                trend_state=result["trend_state"], source_id=source_id,
                                computed_at=now))
        stored = True
    return stored


def clip_to_range(value: float, value_range: tuple[float | None, float | None] | None) -> float:
    """The value inside the indicator's [min, max] (indicators.yaml -> value_range)."""
    low, high = value_range or (None, None)
    if low is not None:
        value = max(value, low)
    if high is not None:
        value = min(value, high)
    return value


def _store_projection(session, ind: IndicatorConf, key: tuple, points, source_id: int,
                      method: Methodology, now: datetime) -> int:
    _, country, sector, occupation, frequency = key
    session.execute(delete(Observation).where(
        Observation.indicator_code == ind.code, Observation.country_iso3 == country,
        Observation.sector_code.is_not_distinct_from(sector),
        Observation.occupation_code.is_not_distinct_from(occupation),
        Observation.frequency == frequency, Observation.data_type == "projected",
    ))
    forecast = project_series([p.value for p in points], methodology_params("projection"))
    if not forecast:
        return 0
    last = points[-1]

    def clip(v: float) -> float:
        return clip_to_range(v, ind.value_range)

    for f in forecast:
        start, end = shift_period(last.period_start, frequency, f["step"])
        session.add(Observation(
            indicator_code=ind.code, country_iso3=country, sector_code=sector,
            occupation_code=occupation, period_start=start, period_end=end, frequency=frequency,
            value=clip(f["value"]), unit=last.unit, data_type="projected", source_id=source_id,
            methodology_id=method.methodology_id, lower_bound=clip(f["lower_bound"]),
            upper_bound=clip(f["upper_bound"]), source_updated_at=last.source_updated_at,
            fetched_at=now,
        ))
    return len(forecast)


def recompute(session: Session, indicator_codes: list[str] | None = None) -> RecomputeSummary:
    """Recalculate trends and projections for the given indicators (all when None)."""
    now = datetime.now(UTC)
    source_ids = {s.source_code: s.source_id for s in session.scalars(select(Source)).all()}
    projection_method = ensure_methodology(session, "projection")
    summary = RecomputeSummary()
    scope = analytics()["recompute"]["occupation_series"]
    featured = {o.occupation_code for o in catalog().occupations if o.is_featured}
    for key in observed_series_keys(session, indicator_codes):
        ind = indicators().get(key[0])
        occupation = key[3]
        if ind is None or (occupation is not None and (
                scope == "none" or (scope == "featured" and occupation not in featured))):
            continue
        points = [p for p in query_points(session, ind, [key[1]], key[2], key[3],
                                          data_type="observed") if p.frequency == key[4]]
        if not points:
            continue
        source_id = source_ids[points[-1].source.code]
        trend_method = ensure_methodology(session, "trend", ind.trend)
        summary.series += 1
        summary.trends += _store_trend(session, ind, key, points, source_id, trend_method, now)
        summary.projections += _store_projection(session, ind, key, points, source_id,
                                                 projection_method, now)
    prune_superseded(session, TrendResult, "trend", indicator_codes)
    prune_superseded(session, Observation, "projection", indicator_codes)
    if indicator_codes is None or input_indicators() & set(indicator_codes):
        summary.employability_scores = recompute_employability(
            session, ensure_methodology(session, "employability_index"))
        prune_superseded(session, EmployabilityScore, "employability_index")
        summary.skill_gaps = refresh_skill_gaps(session)
    if indicator_codes is None or moctezuma_inputs() & set(indicator_codes):
        summary.moctezuma_scores = refresh_moctezuma(session)
    if indicator_codes is None or moctezuma_inputs("ludita") & set(indicator_codes):
        summary.ludita_scores = refresh_ludita(session)
    if indicator_codes is None:  # full recalculation: also the indicators without input indicators
        summary.red_queen_scores = refresh_red_queen(session)
    from app.analytics.sisyphus import input_indicators as sisyphus_inputs  # import cycle
    if indicator_codes is None or sisyphus_inputs() & set(indicator_codes):
        # computed on request: only the methodology row is kept current (traceability)
        ensure_methodology(session, "sisyphus_index")
    session.flush()
    summary.alerts = evaluate_alerts(session, indicator_codes)
    return summary


def refresh_skill_gaps(session: Session) -> int:
    """Skill gaps depend on employment (demand), graduates (supply) and ESCO (skills)."""
    from app.analytics.skill_gaps_run import recompute_skill_gaps  # avoid an import cycle

    stored = recompute_skill_gaps(session, ensure_methodology(session, "skill_gap"))
    prune_superseded(session, SkillGap, "skill_gap")
    prune_superseded(session, SkillGroupGap, "skill_gap")
    return stored


def refresh_moctezuma(session: Session) -> int:
    """The Moctezuma indicator depends on its input indicators and on graduates (training)."""
    from app.analytics.moctezuma_run import recompute_moctezuma  # avoid an import cycle

    stored = recompute_moctezuma(session, ensure_methodology(session, "moctezuma_index"))
    prune_superseded(session, MoctezumaScore, "moctezuma_index")
    return stored


def refresh_ludita(session: Session) -> int:
    """The Ludita indicator depends on AI exposure, employment and graduates."""
    from app.analytics.ludita_run import recompute_ludita  # avoid an import cycle

    stored = recompute_ludita(session, ensure_methodology(session, "ludita_index"))
    prune_superseded(session, LuditaScore, "ludita_index")
    return stored


def refresh_red_queen(session: Session) -> int:
    """The Reina Roja indicator depends only on the stored skill profiles (skill_versions)."""
    from app.analytics.red_queen_run import recompute_red_queen  # avoid an import cycle
    from app.models import RedQueenScore

    stored = recompute_red_queen(session, ensure_methodology(session, "red_queen_index"))
    prune_superseded(session, RedQueenScore, "red_queen_index")
    return stored


def prune_superseded(session: Session, model, methodology_type: str,
                     indicator_codes: list[str] | None = None) -> int:
    """Delete the results of a calculation made with parameters no longer in the config, for
    the indicators just recomputed (all when None), unless keep_superseded_results is set."""
    if analytics()["recompute"].get("keep_superseded_results"):
        return 0
    current = current_digests(methodology_type)
    superseded = select(Methodology.methodology_id).where(
        Methodology.methodology_type == methodology_type,
        Methodology.params_hash.not_in(current))
    stmt = delete(model).where(model.methodology_id.in_(superseded))
    if indicator_codes is not None and hasattr(model, "indicator_code"):
        stmt = stmt.where(model.indicator_code.in_(indicator_codes))
    return session.execute(stmt).rowcount or 0
