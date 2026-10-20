from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.recompute import recompute
from app.core.database import get_session
from app.ingestion.pipeline import upsert_observations
from app.main import app
from app.models import (
    Base,
    Country,
    IngestionRun,
    Source,
)
from tests.conftest import sqlite_tables

FETCHED = datetime(2026, 10, 17, tzinfo=UTC)


def _obs(source_id, country, year, value, indicator="unemployment_rate", unit="percent"):
    return dict(indicator_code=indicator, country_iso3=country, sector_code=None,
                occupation_code=None, period_start=date(year, 1, 1), period_end=date(year, 12, 31),
                frequency="A", value=value, unit=unit, data_type="observed", source_id=source_id,
                run_id=None, source_updated_at=date(2026, 10, 8), fetched_at=FETCHED)


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(
        engine, tables=sqlite_tables()
    )
    with Session(engine) as s:
        s.add_all([Country(iso3=c, name_es=c, name_en=c) for c in ("ARG", "CHL", "URY")])
        s.add_all([Source(source_id=1, source_code="ilostat", name="ILOSTAT", source_kind="api",
                          expected_frequency="weekly"),
                   Source(source_id=2, source_code="world_bank", name="World Bank",
                          source_kind="api", expected_frequency="weekly")])
        s.add(IngestionRun(source_id=1, started_at=datetime.now(UTC), finished_at=datetime.now(UTC),
                           status="success", triggered_by="manual"))
        upsert_observations(s, [
            _obs(1, "ARG", 2023, 6.1), _obs(1, "ARG", 2024, 7.2),
            _obs(2, "ARG", 2024, 99.0),  # lower-priority source for the same point: ignored
            _obs(1, "CHL", 2023, 8.7), _obs(1, "CHL", 2024, 8.5),
        ])
        upsert_observations(s, [_obs(1, "ARG", 2024, 7.15)])  # re-ingest updates, no duplicate
        # 14 years of rising inflation in URY: enough history for trend and projection
        upsert_observations(s, [_obs(2, "URY", 2011 + i, 5.0 + i, indicator="inflation")
                                for i in range(14)])
        s.commit()
        recompute(s)
        recompute(s)  # idempotent
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_indicators_by_domain(client):
    r = client.get("/api/v1/indicators", params={"domain": "education"}).json()
    assert r and all(i["domain"] == "education" and i["domain_label"] == "Educativos" for i in r)


def test_observations_traceability_and_priority(client):
    r = client.get("/api/v1/observations",
                   params={"indicator": "unemployment_rate", "country": "arg"}).json()
    assert r["total"] == 2
    last = r["items"][-1]
    assert last["value"] == 7.15 and last["source"]["code"] == "ilostat"
    assert last["period"] == "2024" and last["data_type"] == "observed"
    assert last["source_updated_at"] == "2026-10-08" and last["data_type_label"]


def test_compare_in_percentage_points(client):
    r = client.get("/api/v1/compare", params={"indicator": "unemployment_rate"}).json()
    items = {i["country_iso3"]: i for i in r["items"]}
    assert items["ARG"]["change_kind"] == "absolute"
    assert items["ARG"]["change"] == pytest.approx(7.15 - 6.1)
    assert items["URY"]["current"] is None and items["URY"]["change"] is None


def test_dashboard_summary_follows_config(client):
    from app.core.config_files import app_config

    r = client.get("/api/v1/dashboard/summary", params={"country": "CHL"}).json()
    codes = [c["indicator"]["code"] for c in r["highlights"]]
    assert codes == [h.indicator for h in app_config().dashboard.highlights]
    assert r["highlights"][0]["change"] == pytest.approx(8.5 - 8.7)


def test_unknown_indicator_404(client):
    assert client.get("/api/v1/observations", params={"indicator": "nope"}).status_code == 404


def test_sources_status(client):
    r = {s["code"]: s for s in client.get("/api/v1/sources").json()}
    assert r["ilostat"]["status"] == "ok" and r["ilostat"]["has_connector"]
    assert r["world_bank"]["status"] == "never_run"


def test_refresh_requires_api_key(client):
    assert client.post("/api/v1/sources/ilostat/refresh").status_code == 401


def test_trends_state_and_assessment(client):
    r = {(t["indicator"]["code"], t["country_iso3"]): t for t in client.get("/api/v1/trends").json()}
    infl = r[("inflation", "URY")]
    assert infl["trend_state"] == "growing" and infl["assessment"] == "unfavorable"
    assert infl["window_start"] == "2020" and infl["window_end"] == "2024"
    assert infl["data_type"] == "calculated" and infl["source"]["code"] == "world_bank"
    # 2 points only: not enough to classify
    assert r[("unemployment_rate", "ARG")]["trend_state"] == "insufficient_data"


def test_trends_filter_by_state(client):
    r = client.get("/api/v1/trends", params={"state": "growing"}).json()
    assert [t["indicator"]["code"] for t in r] == ["inflation"]


def test_projections_follow_observed(client):
    r = client.get("/api/v1/projections", params={"indicator": "inflation", "country": "URY"}).json()
    series = r["items"][0]
    assert [p["period"] for p in series["projected"]] == ["2025", "2026", "2027", "2028"]
    assert all(p["data_type"] == "projected" and p["lower_bound"] <= p["value"] <= p["upper_bound"]
               for p in series["projected"])
    assert series["methodology"]["methodology_type"] == "projection"
    assert len(series["observed"]) == 14


def test_methodologies_trace_overrides(client):
    rows = client.get("/api/v1/methodologies/trend").json()
    # base parameters (unemployment) and inflation's override (absolute threshold) are two
    # distinct parameter sets, both current
    assert sorted(m["params"]["normalize"] for m in rows) == [False, True]
    assert all(m["is_current"] and m["description_md"] for m in rows)
    assert client.get("/api/v1/methodologies/nope").status_code == 404


def test_trends_over_requested_years(client):
    # URY inflation rises 1 point a year from 2011 to 2024
    r = client.get("/api/v1/trends", params={"indicator": "inflation", "country": "URY",
                                             "from_year": 2013, "to_year": 2016}).json()
    t = r[0]
    assert t["window_mode"] == "range" and (t["window_start"], t["window_end"]) == ("2013", "2016")
    assert t["n_points"] == 4 and t["trend_state"] == "growing"
    assert t["slope"] == pytest.approx(1.0)  # inflation override: absolute points per year
    assert t["methodology"]["methodology_type"] == "trend"
    # latest stored window is unchanged
    latest = client.get("/api/v1/trends", params={"indicator": "inflation"}).json()[0]
    assert latest["window_mode"] == "latest" and latest["window_end"] == "2024"


def test_trends_range_with_too_few_points(client):
    r = client.get("/api/v1/trends", params={"indicator": "inflation", "country": "URY",
                                             "from_year": 2023, "to_year": 2024}).json()
    assert r[0]["trend_state"] == "insufficient_data" and r[0]["assessment"] is None


def test_invalid_year_range(client):
    r = client.get("/api/v1/trends", params={"from_year": 2024, "to_year": 2020})
    assert r.status_code == 422


def test_projections_filter_observed_years_only(client):
    r = client.get("/api/v1/projections", params={"indicator": "inflation", "country": "URY",
                                                  "from_year": 2020}).json()["items"][0]
    assert [p["period"] for p in r["observed"]] == ["2020", "2021", "2022", "2023", "2024"]
    assert len(r["projected"]) == 4


def test_revised_source_values_keep_their_history(client):
    revs = client.get("/api/v1/sources/ilostat/revisions").json()
    # the fixture re-ingests ARG 2024 (7.2 -> 7.15): the old value is kept, the unchanged ones not
    assert len(revs) == 1
    r = revs[0]
    assert r["dataset"] == "observations" and r["change"] == "revised"
    assert (r["old_value"], r["new_value"]) == (7.2, 7.15)
    assert r["record_key"]["country_iso3"] == "ARG" and r["record_key"]["period_start"] == "2024-01-01"
    assert client.get("/api/v1/sources/ilostat/revisions", params={"dataset": "graduates"}).json() == []
