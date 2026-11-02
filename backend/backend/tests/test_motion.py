from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.employability_run import Point
from app.analytics.motion import roll_up, with_carry, year_over_year
from app.core.config_files import catalog
from app.core.database import get_session
from app.ingestion.pipeline import upsert_observations
from app.main import app
from app.models import Base, Country, Source
from tests.conftest import sqlite_tables

FETCHED = datetime(2026, 10, 31, tzinfo=UTC)


def _pts(*pairs):
    return [Point(y, v, "ilostat", None) for y, v in pairs]


def test_each_source_group_counts_once():
    # 2511 and 2512 share the 2-digit group 25; 2221 is group 22
    points = {("ARG", "2511"): _pts((2023, 100)), ("ARG", "2512"): _pts((2023, 100)),
              ("ARG", "2221"): _pts((2023, 50))}
    assert roll_up(points, {"ARG": 2}, 1, "sum") == {("ARG", "2", 2023): 150}
    assert roll_up(points, {"ARG": 2}, 1, "mean") == {("ARG", "2", 2023): 75}
    # per-occupation tables (no source digits): every occupation counts
    assert roll_up(points, {}, 1, "mean")[("ARG", "2", 2023)] == pytest.approx(250 / 3)
    # characteristics apply their latest value to every year asked
    assert roll_up({("ARG", "2512"): _pts((2025, .5))}, {}, 1, "mean", [2020, 2021]) == {
        ("ARG", "2", 2020): .5, ("ARG", "2", 2021): .5}


def test_growth_and_carry():
    values = {("ARG", "2", 2022): 20, ("ARG", "2", 2023): 25, ("ARG", "3", 2022): 100,
              ("ARG", "3", 2023): 110}
    assert year_over_year(values) == {("ARG", "2", 2023): 25, ("ARG", "3", 2023): pytest.approx(10)}
    assert year_over_year(values, min_base=30) == {("ARG", "3", 2023): pytest.approx(10)}
    assert with_carry(values, ("ARG", "2", 2024), 1) == (25, 2023)
    assert with_carry(values, ("ARG", "2", 2025), 1) is None


def _obs(indicator, country, occupation, year, value, unit):
    return dict(indicator_code=indicator, country_iso3=country, sector_code=None,
                occupation_code=occupation, period_start=date(year, 1, 1),
                period_end=date(year, 12, 31), frequency="A", value=value, unit=unit,
                data_type="observed", source_id=1, run_id=None,
                source_updated_at=None, fetched_at=FETCHED)


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=sqlite_tables())
    with Session(engine) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en)
                   for c in catalog().countries])
        s.add(Source(source_id=1, source_code="ilostat", name="ILOSTAT", source_kind="api"))
        rows = []
        for year, emp in ((2022, 200), (2023, 220), (2024, 231)):
            # Argentina publishes employment by 2-digit group: 2511 and 2512 share 25
            for occ in ("2511", "2512"):
                rows.append(_obs("employment", "ARG", occ, year, emp, "thousands_persons"))
            rows.append(_obs("employment", "ARG", "2221", year, 100, "thousands_persons"))
        for year in (2022, 2023):  # earnings stop a year earlier than employment
            for occ in ("2511", "2512", "2221"):
                rows.append(_obs("mean_monthly_earnings_usd", "ARG", occ, year, 1000 + year,
                                 "usd_month"))
                rows.append(_obs("mean_monthly_earnings_ppp", "ARG", occ, year, 2000 + year,
                                 "ppp_usd_month"))
        upsert_observations(s, rows)
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_motion_bubbles(client):
    r = client.get("/api/v1/occupation-groups/motion", params={"country": "ARG"}).json()
    assert r["y"]["key"] == "growth" and r["y"]["unit"] == "percent"
    assert {o["key"] for o in r["y_options"]} == {"growth", "ai_exposure", "employability"}
    assert r["groups"][0]["code"] == "2" and r["groups"][0]["name"]
    pts = {p["year"]: p for p in r["points"]}
    assert sorted(pts) == [2023, 2024]  # 2022 has no previous year
    assert pts[2023]["size"] == 320 and pts[2023]["y"] == pytest.approx(20 / 300 * 100)
    # 2024 earnings are carried from 2023 and flagged
    # salaries in USD, with the USD PPA value of the same year next to them
    assert r["x"]["unit"] == "usd_month" and r["x_secondary"]["unit"] == "ppp_usd_month"
    assert pts[2023]["x"] == 3023 and pts[2023]["x_secondary"] == 4023
    assert pts[2024]["x"] == 3023 and pts[2024]["carried"] == {"x": 2023}
    assert pts[2024]["x_secondary"] == 4023
    assert client.get("/api/v1/occupation-groups/motion", params={"y": "nope"}).status_code == 422
