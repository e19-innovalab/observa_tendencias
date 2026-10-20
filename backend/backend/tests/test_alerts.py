from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.alerts import significant_change
from app.analytics.alerts_run import evaluate_alerts
from app.analytics.recompute import recompute
from app.core import config as core_config
from app.core.config_files import catalog
from app.core.database import get_session
from app.ingestion.pipeline import upsert_observations
from app.main import app
from app.models import (
    Alert,
    Base,
    Country,
    Source,
)
from tests.conftest import sqlite_tables

FETCHED = datetime(2026, 10, 17, tzinfo=UTC)
THIS_YEAR = datetime.now(UTC).year


def test_points_mode_for_rates():
    # unemployment 6.1 -> 7.2: +1.1 points crosses the 1.0 threshold although 6.1 < min_base
    found = significant_change([6.0, 6.2, 6.1, 7.2], absolute=True)
    assert found and "puntos" in found["message"] and found["severity"] == "medium"
    assert significant_change([6.0, 6.1, 6.2, 6.5], absolute=True) is None
    assert significant_change([219.9, 41.9], absolute=True)["severity"] == "high"
    # relative mode keeps ignoring tiny bases
    assert significant_change([6.1, 7.2]) is None


def _obs(source_id, indicator, country, year, value, unit, occupation=None, sector=None):
    return dict(indicator_code=indicator, country_iso3=country, sector_code=sector,
                occupation_code=occupation, period_start=date(year, 1, 1),
                period_end=date(year, 12, 31), frequency="A", value=value, unit=unit,
                data_type="observed", source_id=source_id, run_id=None,
                source_updated_at=None, fetched_at=FETCHED)


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng, tables=sqlite_tables())
    y = THIS_YEAR - 1
    with Session(eng) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en)
                   for c in catalog().countries])
        s.add_all([Source(source_id=1, source_code="ilostat", name="ILOSTAT", source_kind="api",
                          expected_frequency="weekly"),
                   Source(source_id=2, source_code="world_bank", name="World Bank",
                          source_kind="api", expected_frequency="weekly")])
        rows = [
            # rate: steady, then +2.5 points in the latest year -> high (>2x the 1.0 threshold)
            *[_obs(1, "unemployment_rate", "ARG", y - 6 + i, 6.0 + 0.05 * i, "percent")
              for i in range(6)],
            _obs(1, "unemployment_rate", "ARG", y, 8.75, "percent"),
            # gap: Chile 2 years apart -> not consecutive, no alert
            _obs(1, "unemployment_rate", "CHL", y - 2, 6.0, "percent"),
            _obs(1, "unemployment_rate", "CHL", y, 9.0, "percent"),
            # old data: a jump that ended years ago -> no alert
            _obs(1, "unemployment_rate", "URY", y - 5, 6.0, "percent"),
            _obs(1, "unemployment_rate", "URY", y - 4, 9.0, "percent"),
        ]
        # one ISCO 25 group value shared by the four featured IT occupations: +20%
        for occ in ("2511", "2512", "2513", "2523"):
            rows += [_obs(1, "employment", "ARG", y - 1, 100.0, "thousands_persons", occ),
                     _obs(1, "employment", "ARG", y, 120.0, "thousands_persons", occ)]
        upsert_observations(s, rows)
        s.commit()
        recompute(s)
        s.commit()
    return eng


def test_rules_dedupe_and_grouping(engine):
    with Session(engine) as s:
        alerts = s.scalars(select(Alert).where(Alert.alert_type == "significant_change")).all()
        by_country = {(a.indicator_code, a.country_iso3) for a in alerts}
        assert ("unemployment_rate", "ARG") in by_country
        assert ("unemployment_rate", "CHL") not in by_country  # gap
        assert ("unemployment_rate", "URY") not in by_country  # too old
        arg = next(a for a in alerts if a.indicator_code == "unemployment_rate")
        assert arg.severity == "high" and arg.previous_value == pytest.approx(6.25)
        it = [a for a in alerts if a.indicator_code == "employment"]
        assert len(it) == 1 and it[0].occupation_code == "2511"
        assert "grupo CIUO 25" in it[0].message and "Desarrollador/a de software" in it[0].message
        before = s.scalar(select(func.count()).select_from(Alert))
        assert evaluate_alerts(s) == 0  # same data: nothing new
        assert s.scalar(select(func.count()).select_from(Alert)) == before


def test_trend_reversal_from_previous_window(engine):
    with Session(engine) as s:
        rev = s.scalars(select(Alert).where(Alert.alert_type == "trend_reversal",
                                            Alert.indicator_code == "unemployment_rate")).all()
        # ARG: stable while rising 0.05 a year, then the jump makes the last window grow
        assert [(a.country_iso3, a.previous_state, a.current_state) for a in rev] == [
            ("ARG", "stable", "growing")]
        assert "Estabilidad a Crecimiento" in rev[0].message


@pytest.fixture
def client(engine, monkeypatch):
    def override():
        with Session(engine) as s:
            yield s

    monkeypatch.setattr(core_config.settings, "admin_api_key", "test-key")
    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_alerts_api_filters_and_read(client):
    r = client.get("/api/v1/alerts").json()
    assert r["total"] == r["unread"] > 0 and r["by_severity"]["high"] >= 1
    high = client.get("/api/v1/alerts", params={"severity": "high", "country": "ARG"}).json()
    item = high["items"][0]
    assert item["severity_label"] == "Alta" and item["alert_type_label"]
    assert item["indicator"]["name"] and item["unit"] == "percent"
    aid = item["alert_id"]
    assert client.patch(f"/api/v1/alerts/{aid}", json={"is_read": True}).status_code == 401
    ok = client.patch(f"/api/v1/alerts/{aid}", json={"is_read": True},
                      headers={"X-API-Key": "test-key"})
    assert ok.status_code == 200 and ok.json()["is_read"] is True
    assert client.get("/api/v1/alerts").json()["unread"] == r["unread"] - 1
    done = client.post("/api/v1/alerts/read-all", headers={"X-API-Key": "test-key"}).json()
    assert done["updated"] == r["unread"] - 1
    assert client.get("/api/v1/alerts", params={"unread": "true"}).json()["total"] == 0
    assert client.patch("/api/v1/alerts/99999", json={"is_read": True},
                        headers={"X-API-Key": "test-key"}).status_code == 404


def test_alert_rules_reflect_config(client):
    from app.core.config_files import analytics_params

    r = client.get("/api/v1/alerts/rules").json()
    p = analytics_params("alerts")
    rules = {x["alert_type"]: x for x in r["rules"]}
    sig = rules["significant_change"]
    assert sig["params"]["change_pct"] == p["change_pct"]
    assert sig["params"]["absolute_change"] == p["absolute_change"]
    assert sig["definition"] and "Alta" in sig["severity_rule"]
    assert rules["new_skill_gap"]["active"] is False
    assert {s["code"] for s in r["severities"]} == {"high", "medium", "low"}
    assert all(s["definition"] for s in r["severities"])
    assert {"indicator": {"code": "gdp_growth", "name": "Crecimiento del PBI"},
            "params": {"absolute_change": 3.0}} in r["overrides"]
    assert r["methodology"]["methodology_type"] == "alert" and r["methodology"]["description_md"]


def test_alerts_point_to_a_methodology(engine):
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Alert).where(
            Alert.methodology_id.is_(None))) == 0
