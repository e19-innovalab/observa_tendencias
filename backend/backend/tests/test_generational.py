from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config_files import catalog
from app.core.database import get_session
from app.ingestion.pipeline import upsert_observations
from app.main import app
from app.models import Base, Country, Source
from tests.conftest import sqlite_tables

FETCHED = datetime(2026, 11, 1, tzinfo=UTC)


def _obs(indicator, year, value):
    return dict(indicator_code=indicator, country_iso3="URY", sector_code=None, occupation_code=None,
                period_start=date(year, 1, 1), period_end=date(year, 12, 31), frequency="A",
                value=value, unit="percent", data_type="observed", source_id=1, run_id=None,
                source_updated_at=None, fetched_at=FETCHED)


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=sqlite_tables())
    with Session(engine) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en) for c in catalog().countries])
        s.add(Source(source_id=1, source_code="ilostat", name="ILOSTAT", source_kind="api"))
        upsert_observations(s, [_obs("youth_unemployment_rate_survey", 2024, 24.0),
                                _obs("unemployment_rate", 2024, 8.0),
                                _obs("unemployment_rate", 2025, 7.0)])  # no youth rate in 2025
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_gap_uses_years_with_both_rates(client):
    r = client.get("/api/v1/generational-gap", params={"country": "URY"}).json()
    c = r["countries"][0]
    assert [p["year"] for p in c["points"]] == [2024]
    assert c["latest"]["ratio"] == pytest.approx(3.0)
    assert "3,0 veces" in c["headline"] and "(2024)" in c["headline"]
    assert r["source"] == "ILOSTAT"
