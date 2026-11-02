from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.sisyphus import latest, not_applicable_groups
from app.core.config_files import analytics_params, catalog
from app.core.database import get_session
from app.ingestion.pipeline import upsert_observations
from app.main import app
from app.models import Base, Country, EducationMismatchCell, Source
from tests.conftest import sqlite_tables

FETCHED = datetime(2026, 11, 1, tzinfo=UTC)
P = analytics_params("sisyphus")


def test_helpers():
    assert latest({2022: 1.0, 2024: 2.0}, 2025, 2) == (2.0, 2024)
    assert latest({2020: 1.0}, 2025, 2) is None
    # groups 1-3 require tertiary education in the ILO norm: they cannot be overeducated
    assert not_applicable_groups(P) == {"1", "2", "3"}


def _obs(indicator, occupation, value, unit, year=2024):
    return dict(indicator_code=indicator, country_iso3="ARG", sector_code=None,
                occupation_code=occupation, period_start=date(year, 1, 1),
                period_end=date(year, 12, 31), frequency="A", value=value, unit=unit,
                data_type="observed", source_id=1, run_id=None, source_updated_at=None,
                fetched_at=FETCHED)


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=sqlite_tables())
    with Session(engine) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en)
                   for c in catalog().countries])
        s.add(Source(source_id=1, source_code="ilostat", name="ILOSTAT", source_kind="api"))
        rows = []
        # group 9 (elementary): very overeducated and badly paid; group 4 (clerks): the opposite;
        # group 2 cannot be overeducated and is left out
        for occ, over, earn in (("9112", 70.0, 600.0), ("4110", 10.0, 1500.0), ("2512", 0.0, 2500.0)):
            rows.append(_obs("overeducation_rate", occ, over, "percent"))
            rows.append(_obs("mean_monthly_earnings_ppp", occ, earn, "ppp_usd_month"))
            rows.append(_obs("mean_monthly_earnings_usd", occ, earn / 2, "usd_month"))
        rows += [_obs("earnings_tertiary_ppp", None, 2000.0, "ppp_usd_month"),
                 _obs("earnings_secondary_ppp", None, 1250.0, "ppp_usd_month")]
        upsert_observations(s, rows)
        s.add_all([EducationMismatchCell(country_iso3="ARG", year=2024, isco_group=g, band="tertiary",
                                         status=st, employed=n, source_id=1, fetched_at=FETCHED)
                   for g, st, n in (("2", "matched", 300.0), ("4", "over", 100.0))])
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_groups_and_quadrants(client):
    r = client.get("/api/v1/sisyphus", params={"country": "ARG"}).json()
    assert r["year"] == 2024 and r["excluded_groups"] == ["1", "2", "3"]
    items = {i["group_code"]: i for i in r["items"]}
    assert set(items) == {"4", "9"}  # group 2 left out
    assert r["items"][0]["group_code"] == "9" and items["9"]["score"] == 100
    assert items["9"]["earnings_ratio"] == pytest.approx(0.3)  # 600 / 2000
    assert items["9"]["quadrant"] == "sisyphus" and items["4"]["quadrant"] == "fits"
    assert items["9"]["earnings_usd"] == 300 and items["9"]["tertiary_ppp"] == 2000
    country = client.get("/api/v1/sisyphus/countries", params={"country": "ARG"}).json()[0]
    point = next(p for p in country["points"] if p["year"] == 2024)
    assert point["graduates_below_share"] == pytest.approx(0.25)  # 100 of 400
    assert point["premium"] == pytest.approx(0.6)  # 2000 / 1250 - 1
