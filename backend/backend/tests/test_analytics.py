from datetime import datetime, timedelta, timezone

from app.analytics.alerts import evaluate_alert_rules, significant_change
from app.analytics.employability import compute_employability_index
from app.analytics.projections import project_series
from app.analytics.skill_gaps import compute_skill_gaps
from app.analytics.trends import classify_trend


def test_trend_states():
    assert classify_trend([100, 105, 110, 116, 122])["trend_state"] == "growing"
    assert classify_trend([122, 116, 110, 105, 100])["trend_state"] == "declining"
    assert classify_trend([100, 100.1, 99.9, 100, 100])["trend_state"] == "stable"
    assert classify_trend([1, 2])["trend_state"] == "insufficient_data"


def test_projection_needs_history():
    assert project_series(list(range(5))) is None
    out = project_series([float(i) for i in range(1, 25)])
    assert len(out) == 4 and out[0]["lower_bound"] <= out[0]["value"] <= out[0]["upper_bound"]


def test_employability_relative_and_coverage():
    cohort = {
        "a": {"net_demand": 10, "salary_ppp": 10, "insertion_rate": 80, "automation_risk": 5},
        "b": {"net_demand": 0, "salary_ppp": 0, "insertion_rate": 20, "automation_risk": 20},
        "c": {"net_demand": 5, "salary_ppp": None, "insertion_rate": None, "automation_risk": None},
    }
    res = compute_employability_index(cohort)
    assert res["a"]["score"] == 100 and res["a"]["level"] == "high"
    assert res["b"]["score"] == 0 and res["b"]["level"] == "low"
    assert res["c"]["level"] == "insufficient_data" and res["c"]["score"] is None


def test_skill_gaps_never_invent():
    out = compute_skill_gaps(
        {"x": {"demand": 80, "supply": 30}, "y": {"demand": 50, "supply": None}}
    )
    assert out[0]["gap_score"] == 50 and out[1]["gap_score"] is None
    assert out[1]["data_sufficiency"] == "partial"


def test_alerts():
    assert significant_change([100, 101, 100, 101, 130])["alert_type"] == "significant_change"
    assert significant_change([100, 101]) is None
    assert significant_change([1, 34]) is None  # tiny base: +3300% is noise
    assert significant_change([1, 34], {"min_base": 0}) is not None
    old = datetime.now(timezone.utc) - timedelta(days=100)
    alerts = evaluate_alert_rules(
        {"level": "high", "prev_level": "medium", "last_update": old, "expected_days": 30}
    )
    assert {a["alert_type"] for a in alerts} == {"index_level_change", "stale_source"}
