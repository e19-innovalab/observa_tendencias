from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.moctezuma import compute_moctezuma_index
from app.analytics.recompute import recompute
from app.core.config_files import analytics_params, catalog
from app.core.database import get_session
from app.ingestion.pipeline import upsert_observations
from app.main import app
from app.models import Base, Country, Methodology, MoctezumaScore, Source
from tests.conftest import sqlite_tables

FETCHED = datetime(2026, 10, 31, tzinfo=UTC)
P = analytics_params("moctezuma")


def test_index_is_pace_against_readiness():
    cohort = {
        "fast": {"ai_exposure": 0.6, "digital_diffusion": 0.05, "training_growth": 0.0,
                 "education_fit": 30, "tertiary_base": 60},
        "slow": {"ai_exposure": 0.2, "digital_diffusion": 0.01, "training_growth": 0.1,
                 "education_fit": 10, "tertiary_base": 90},
    }
    res = compute_moctezuma_index(cohort, P)
    # fast: top pace (100), lowest readiness (0) -> 100; slow: the opposite -> 0
    assert res["fast"]["score"] == pytest.approx(100) and res["fast"]["level"] == "high"
    assert res["slow"]["score"] == pytest.approx(0) and res["slow"]["level"] == "low"
    assert res["fast"]["gap"] == pytest.approx(100)
    # undereducation counts against readiness: the higher one scales to 0
    assert res["fast"]["components"]["education_fit"]["normalized"] == 0


def test_missing_weight_is_redistributed_within_the_side():
    cohort = {
        "a": {"ai_exposure": 0.6, "digital_diffusion": None, "training_growth": None,
              "education_fit": 30, "tertiary_base": 60},
        "b": {"ai_exposure": 0.2, "digital_diffusion": None, "training_growth": None,
              "education_fit": 10, "tertiary_base": 90},
    }
    res = compute_moctezuma_index(cohort, P)
    assert res["a"]["coverage"] == {"pace": 0.5, "readiness": pytest.approx(2 / 3)}
    assert res["a"]["pace"] == 100 and res["a"]["readiness"] == 0


def test_without_one_side_there_is_no_asymmetry():
    cohort = {k: {"ai_exposure": v, "digital_diffusion": 0.02, "training_growth": None,
                  "education_fit": None, "tertiary_base": None} for k, v in (("a", .5), ("b", .1))}
    res = compute_moctezuma_index(cohort, P)
    assert res["a"]["score"] is None and res["a"]["level"] == "insufficient_data"


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
    exposure = {"2512": 0.53, "2221": 0.25, "5120": 0.18}
    under = {"2512": 5.0, "2221": 8.0, "5120": 40.0}
    with Session(engine) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en)
                   for c in catalog().countries])
        s.add_all([Source(source_id=1, source_code="ilostat", name="ILOSTAT", source_kind="api"),
                   Source(source_id=2, source_code="ilo_genai_exposure", name="OIT",
                          source_kind="dataset"),
                   Source(source_id=3, source_code="world_bank", name="Banco Mundial",
                          source_kind="api")])
        rows = []
        for occ in exposure:
            rows.append(_obs(2, "genai_exposure", "ARG", occ, 2025, exposure[occ], "index_0_1"))
            rows.append(_obs(1, "undereducation_rate", "ARG", occ, 2024, under[occ], "percent"))
            rows.append(_obs(2, "genai_exposure", "URY", occ, 2025, exposure[occ], "index_0_1"))
            rows.append(_obs(1, "undereducation_rate", "URY", occ, 2024, under[occ] + 10,
                             "percent"))
        for country, users, tertiary in (("ARG", (80, 85, 88, 90), 95), ("URY", (85, 87, 88, 89), 70)):
            for year, v in zip(range(2021, 2025), users, strict=True):
                rows.append(_obs(3, "internet_users", country, None, year, v, "percent"))
            rows.append(_obs(3, "tertiary_enrollment", country, None, 2023, tertiary, "percent"))
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


def test_ranking_traces_both_sides(client):
    c, engine = client
    r = c.get("/api/v1/moctezuma", params={"country": "ARG,URY"}).json()
    assert r["year"] == 2024 and r["side_labels"]["pace"] == "Ritmo del cambio"
    sides = {x["side"]: x for x in r["sides"]}
    assert sides["pace"]["definition"] and sides["readiness"]["definition"]
    assert [d["dimension"] for d in sides["pace"]["dimensions"]] == ["ai_exposure",
                                                                     "digital_diffusion"]
    assert all(d["definition"] for x in r["sides"] for d in x["dimensions"])
    items = r["items"]
    assert items and all(i["score"] is not None for i in items)
    assert [i["score"] for i in items] == sorted((i["score"] for i in items), reverse=True)
    top = items[0]
    # Uruguay: faster-growing gap between digitalization and a smaller tertiary base
    assert (top["country_iso3"], top["occupation"]["occupation_code"]) == ("URY", "2512")
    comps = {x["dimension"]: x for x in top["components"]}
    assert comps["digital_diffusion"]["scope"] == "country"
    assert comps["training_growth"]["available"] is False  # no graduates loaded
    assert top["readiness_coverage"] == pytest.approx(2 / 3)
    assert top["gap"] == pytest.approx(top["pace"] - top["readiness"])
    bottom = c.get("/api/v1/moctezuma", params={"country": "ARG,URY", "view": "bottom"}).json()
    assert bottom["items"][0]["score"] == min(i["score"] for i in items)
    with Session(engine) as s:
        m = s.scalar(select(Methodology).where(Methodology.methodology_type == "moctezuma_index"))
        assert m.params["side_weights"] == {"pace": 0.5, "readiness": 0.5}
        assert s.scalar(select(MoctezumaScore).where(
            MoctezumaScore.methodology_id != m.methodology_id)) is None


def test_countries_without_data_and_history(client):
    c, _ = client
    chl = c.get("/api/v1/moctezuma", params={"country": "CHL", "view": "all"}).json()
    assert chl["items"] and chl["scored_total"] == 0
    hist = c.get("/api/v1/moctezuma/history",
                 params={"occupation": "2512", "country": "ARG"}).json()[0]
    assert hist["points"][-1]["year"] == 2024 and hist["points"][-1]["score"] is not None
    assert c.get("/api/v1/moctezuma/history", params={"occupation": "nope"}).status_code == 404
    countries = {x["country_iso3"]: x for x in c.get("/api/v1/moctezuma/countries").json()}
    arg = countries["ARG"]["points"][-1]
    rows = c.get("/api/v1/moctezuma", params={"country": "ARG", "view": "all",
                                              "limit": 500}).json()
    scored = [i for i in rows["items"] if i["score"] is not None]
    assert arg["year"] == 2024 and arg["scored"] == len(scored)
    assert arg["score"] == pytest.approx(sum(i["score"] for i in scored) / len(scored))
    # linear formula: the country mean is also 0.5·pace + 0.5·(100 − readiness)
    assert arg["score"] == pytest.approx(0.5 * arg["pace"] + 0.5 * (100 - arg["readiness"]))
    assert countries["CHL"]["points"] == []
    rng = rows["dimension_ranges"]["ai_exposure"]
    assert (rng["observed_min"], rng["observed_max"]) == (0.18, 0.53)
    feat = c.get("/api/v1/moctezuma", params={"featured": "true", "view": "all"}).json()
    assert feat["items"] and all(i["occupation"]["is_featured"] for i in feat["items"])
    m = c.get("/api/v1/methodologies/moctezuma_index")
    assert m.status_code == 200


def test_reference_uses_the_indicator_formula(client):
    c, _ = client
    r = c.get("/api/v1/moctezuma/reference").json()
    pts = {p["year"]: p for p in r["points"]}
    base = pts[r["base_year"]]
    assert base["readiness"] == 100 and base["pace"] == 0 and base["score"] == 0
    ex = pts[r["example_year"]]
    w = P["side_weights"]
    expected = (w["pace"] * ex["pace"] + w["readiness"] * (100 - ex["readiness"])) / sum(w.values())
    assert ex["score"] == pytest.approx(expected)
    assert r["alternative"]["readiness"] == pytest.approx(
        r["alternative"]["population"] / r["alternative"]["base_population"] * 100)
    assert r["sources"]["series"] and r["sources"]["debate"]
    assert r["example_occupation"] and set(r["side_history"]) == {"pace", "readiness"}
