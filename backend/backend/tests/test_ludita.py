from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.ludita_run import path_for
from app.analytics.recompute import recompute
from app.core.config_files import analytics_params, catalog
from app.core.database import get_session
from app.ingestion.pipeline import upsert_observations
from app.main import app
from app.models import Base, Country, LuditaScore, Methodology, Source
from tests.conftest import sqlite_tables

FETCHED = datetime(2026, 10, 31, tzinfo=UTC)
PATHS = analytics_params("ludita")["paths"]


def _comp(exposure, *growth):
    out = {"ai_exposure": {"raw": exposure, "side": "exposure", "weight": 1}}
    for i, g in enumerate(growth):
        out[f"g{i}"] = {"raw": g, "side": "vitality", "weight": 1}
    return out


def test_paths_use_raw_values():
    assert path_for(_comp(0.55, -0.05, None), "vitality", PATHS) == "weaver"
    assert path_for(_comp(0.55, -0.05, 0.10), "vitality", PATHS) == "teller"  # mean +2.5 %
    assert path_for(_comp(0.20, -0.01), "vitality", PATHS) == "other_causes"
    assert path_for(_comp(0.20, 0.03), "vitality", PATHS) == "out_of_reach"
    assert path_for(_comp(0.55, None), "vitality", PATHS) is None  # no vitality data


def _obs(source_id, indicator, country, occupation, year, value, unit):
    return dict(indicator_code=indicator, country_iso3=country, sector_code=None,
                occupation_code=occupation, period_start=date(year, 1, 1),
                period_end=date(year, 12, 31), frequency="A", value=value, unit=unit,
                data_type="observed", source_id=source_id, run_id=None,
                source_updated_at=None, fetched_at=FETCHED)


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=sqlite_tables())
    exposure = {"4110": 0.55, "2512": 0.53, "5120": 0.18}
    # employment by 2-digit group (Argentina): clerical shrinks, software and cooks grow
    employment = {"41": (300, 290, 280, 270), "25": (100, 110, 120, 130), "51": (200, 204, 208, 212)}
    with Session(engine) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en)
                   for c in catalog().countries])
        s.add_all([Source(source_id=1, source_code="ilostat", name="ILOSTAT", source_kind="api"),
                   Source(source_id=2, source_code="ilo_genai_exposure", name="OIT",
                          source_kind="dataset")])
        rows = []
        for occ, e in exposure.items():
            rows.append(_obs(2, "genai_exposure", "ARG", occ, 2025, e, "index_0_1"))
            for year, v in zip(range(2022, 2026), employment[occ[:2]], strict=True):
                rows.append(_obs(1, "employment", "ARG", occ, year, v, "thousands_persons"))
        upsert_observations(s, rows)
        s.commit()
        recompute(s)
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app), engine
    app.dependency_overrides.clear()


def test_ranking_and_paths(client):
    c, engine = client
    r = c.get("/api/v1/ludita", params={"country": "ARG", "year": 2025}).json()
    assert {s["side"] for s in r["sides"]} == {"exposure", "vitality"}
    assert [p["path"] for p in r["paths"]] == ["weaver", "teller", "other_causes", "out_of_reach"]
    by_occ = {i["occupation"]["occupation_code"]: i for i in r["items"]}
    # exposed and shrinking: the weaver's path, and the top of the ranking
    assert r["items"][0]["occupation"]["occupation_code"] == "4110"
    assert by_occ["4110"]["path"] == "weaver" and by_occ["4110"]["path_label"] == "Camino del tejedor"
    assert by_occ["2512"]["path"] == "teller"
    assert by_occ["5120"]["path"] == "out_of_reach"
    assert by_occ["4110"]["score"] > 50 > by_occ["5120"]["score"]
    countries = c.get("/api/v1/ludita/countries", params={"country": "ARG"}).json()[0]
    assert countries["points"][-1]["paths"]["weaver"] >= 1
    with Session(engine) as s:
        m = s.scalar(select(Methodology).where(Methodology.methodology_type == "ludita_index"))
        assert m.params["sides"] == ["exposure", "vitality"]
        assert s.scalar(select(LuditaScore).where(LuditaScore.occupation_code == "4110")) is not None


def test_history_is_indexed_to_the_arrival(client):
    c, _ = client
    h = c.get("/api/v1/ludita/history", params={"country": "ARG"}).json()
    cases = {x["key"]: x for x in h["cases"]}
    assert set(cases) == {"weaver", "telephone_operator", "teller"}
    weaver = {p["year"]: p for p in cases["weaver"]["points"]}
    assert weaver[1813]["index"] == 100 and weaver[1813]["years_since"] == 0
    assert weaver[1862]["index"] < 2 and cases["weaver"]["sources"][0]["url"].startswith("https://")
    assert any(p["approx"] for p in cases["teller"]["points"])
    today = h["today"][0]
    # group 4 (clerical) rolled up from the 2-digit group 41, indexed to 2022
    assert today["country_iso3"] == "ARG" and today["points"][0]["index"] == 100
    assert today["points"][-1]["index"] == pytest.approx(90)
