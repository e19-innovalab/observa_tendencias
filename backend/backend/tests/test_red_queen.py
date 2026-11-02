from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.recompute import refresh_red_queen
from app.analytics.red_queen import annual_turnover, half_life, reconcile, turnover
from app.analytics.red_queen_run import pair_for_year
from app.core.config_files import analytics_params, catalog
from app.core.database import get_session
from app.main import app
from app.models import Base, Country, SkillProfile, Source
from tests.conftest import sqlite_tables

P = analytics_params("red_queen")
NOW = datetime(2026, 11, 1, tzinfo=UTC)


def test_turnover_and_half_life():
    assert turnover({"a", "b", "c"}, {"a", "b", "d"}) == pytest.approx(0.5)  # 2 shared of 4
    # half of the profile changes in 3 years: what stays per year is 0.5^(1/3)
    annual = annual_turnover(0.5, 3)
    assert annual == pytest.approx(1 - 0.5 ** (1 / 3))
    assert half_life(annual, 50) == pytest.approx(3)
    assert half_life(0, 50) == 50  # a profile that does not change: the cap


def test_renamed_items_are_not_changes():
    before = {"adobe systems adobe acrobat", "confluence", "sql"}
    after = {"adobe acrobat", "atlassian confluence", "sql", "python"}
    renamed = reconcile(before, after, 5)
    assert renamed == {"adobe acrobat": "adobe systems adobe acrobat",
                       "atlassian confluence": "confluence"}
    # "sql" is too short to match inside another name
    assert reconcile({"sql"}, {"mysql server"}, 5) == {}


def test_each_year_compares_with_a_version_window_years_older():
    v = [(date(2020, 11, 1), "25.1", {}), (date(2021, 8, 1), "26.0", {}),
         (date(2023, 8, 1), "28.0", {}), (date(2026, 8, 1), "31.0", {})]
    params = {**P, "window_years": 3, "min_years": 1, "max_age_years": 3}
    earlier, later = pair_for_year(v, 2026, params)
    assert (earlier[1], later[1]) == ("28.0", "31.0")
    # nothing 3 years older than 28.0: the oldest one, 2.75 years before
    assert [x[1] for x in pair_for_year(v, 2023, params)] == ["25.1", "28.0"]
    assert pair_for_year(v, 2021, params) is None  # 26.0 is less than a year after 25.1


def _items(names):
    return {n.casefold(): n for n in names}


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=sqlite_tables())
    common = [f"tool {i}" for i in range(30)]
    with Session(engine) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en)
                   for c in catalog().countries])
        s.add_all([Source(source_id=1, source_code="onet_technology", name="O*NET", source_kind="dataset"),
                   Source(source_id=2, source_code="esco_versions", name="ESCO", source_kind="api")])
        for version, released, extra_dev, extra_cook in (
                ("28.0", date(2023, 8, 1), [], []),
                ("31.0", date(2026, 8, 1), [f"new {i}" for i in range(9)], ["new oven"])):
            s.add(SkillProfile(source_code="onet_technology", version=version, released=released,
                               occupation_code="2512", items=_items(common + extra_dev), fetched_at=NOW))
            s.add(SkillProfile(source_code="onet_technology", version=version, released=released,
                               occupation_code="5120", items=_items(common + extra_cook), fetched_at=NOW))
        s.commit()
        refresh_red_queen(s)
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_ranking_by_new_items_per_year(client):
    r = client.get("/api/v1/red-queen", params={"year": 2026}).json()
    assert r["year"] == 2026 and {d["source_code"] for d in r["dimensions"]} == {
        "onet_technology", "esco_versions"}
    items = {i["occupation"]["occupation_code"]: i for i in r["items"]}
    dev, cook = items["2512"], items["5120"]
    assert r["items"][0]["occupation"]["occupation_code"] == "2512"
    tech = next(c for c in dev["components"] if c["dimension"] == "technology_turnover")
    assert (tech["from_version"], tech["to_version"], tech["added_count"]) == ("28.0", "31.0", 9)
    assert tech["new_per_year"] == pytest.approx(9 / tech["years"], rel=1e-3)  # years is rounded
    assert "new 0" in tech["added"] and tech["removed"] == []
    assert dev["score"] == 100 and cook["score"] == 0
    # no ESCO profiles: that dimension is missing and its weight goes to O*NET
    assert dev["coverage"] == pytest.approx(0.5)
    years = client.get("/api/v1/red-queen/years").json()
    assert years[-1]["year"] == 2026 and years[-1]["median_half_life"] > 0


def test_career_filter(client):
    careers = client.get("/api/v1/red-queen/careers", params={"country": "URY"}).json()
    assert careers and all(c["occupations"] > 0 for c in careers)
    career = careers[0]["career"]
    r = client.get("/api/v1/red-queen", params={"country": "URY", "career": career,
                                                "view": "all", "limit": 500}).json()
    from app.api.v1.red_queen import career_occupations
    assert r["career"] == career
    assert {i["occupation"]["occupation_code"] for i in r["items"]} <= career_occupations("URY", career)
    assert client.get("/api/v1/red-queen", params={"country": "URY", "career": "no existe"}).status_code == 404
    assert client.get("/api/v1/red-queen/careers", params={"country": "XXX"}).status_code == 404
