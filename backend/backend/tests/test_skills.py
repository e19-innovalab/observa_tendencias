"""ESCO skills: weights per ISCO group, tolerance to broken records, API."""
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config_files import catalog, sources
from app.core.database import get_session
from app.main import app
from app.models import (
    Base,
    Country,
    OccupationSkill,
    Skill,
    Source,
)
from app.skills import esco
from tests.conftest import sqlite_tables

SKILL = "http://data.europa.eu/esco/skill/{}"
KNOW = "http://data.europa.eu/esco/skill-type/knowledge"
DO = "http://data.europa.eu/esco/skill-type/skill"
# ISCO 2512 has two ESCO occupations: "prog" is essential in both, "uml" optional in one
FAKE = {
    "isco/C2512": {"narrowerOccupation": [{"uri": "occ/a"}, {"uri": "occ/b"}]},
    "occ/a": {"hasEssentialSkill": [{"uri": SKILL.format("prog"), "title": "programación", "skillType": KNOW}],
              "hasOptionalSkill": [{"uri": SKILL.format("uml"), "title": "UML", "skillType": KNOW}]},
    "occ/b": {"hasEssentialSkill": [{"uri": SKILL.format("prog"), "title": "programación", "skillType": KNOW},
                                    {"uri": SKILL.format("test"), "title": "probar software", "skillType": DO}]},
    "isco/C5120": {"narrowerOccupation": [{"uri": "occ/broken"}, {"uri": "occ/c"}]},
    "occ/c": {"hasEssentialSkill": [{"uri": SKILL.format("cook"), "title": "cocinar", "skillType": DO}]},
}


def fake_get(fail_codes=("occ/broken",)):
    async def get(client, url, params=None, headers=None):
        key = next((k for k in FAKE if params["uri"].endswith(k)), None)
        if params["uri"].endswith(fail_codes):
            req = httpx.Request("GET", url)
            raise httpx.HTTPStatusError("500", request=req, response=httpx.Response(500, request=req))
        body = {"_links": FAKE.get(key, {})} if key else {"_links": {}}
        return httpx.Response(200, json=body, request=httpx.Request("GET", url))
    return get


@pytest.fixture
def engine(monkeypatch):
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng, tables=sqlite_tables())
    with Session(eng) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en)
                   for c in catalog().countries])
        s.add(Source(source_code="esco", name="ESCO", source_kind="api", expected_frequency="annual"))
        s.commit()
    monkeypatch.setattr(esco, "get_with_retry", fake_get())
    return eng


def test_weights_and_broken_records(engine, monkeypatch):
    monkeypatch.setitem(sources().get("esco").options, "max_failed_share", 1.0)
    with Session(engine) as s:
        groups, rows, skipped = esco.run_esco_source(s, "esco")
        s.commit()
        w = {(o, sk): wt for o, sk, wt in s.execute(select(
            OccupationSkill.occupation_code, OccupationSkill.skill_code, OccupationSkill.weight)
            .where(OccupationSkill.country_iso3 == "ARG")).all()}
    assert w[("2512", "prog")] == 1.0          # essential in both ESCO occupations
    assert w[("2512", "test")] == 0.5          # essential in one of two
    assert w[("2512", "uml")] == 0.25          # optional (0.5) in one of two
    assert w[("5120", "cook")] == 1.0          # the broken occupation is skipped, not counted
    assert skipped == ["5120:broken"] and groups == 2
    with Session(engine) as s:  # same relations for every catalog country
        n = s.scalar(select(func.count()).select_from(OccupationSkill))
        assert n == rows * len(catalog().countries)
        assert s.get(Skill, "test").skill_type == "skill"


def test_too_many_failures_replace_nothing(engine, monkeypatch):
    monkeypatch.setitem(sources().get("esco").options, "max_failed_share", 0.0)
    with Session(engine) as s, pytest.raises(esco.EscoError):
        esco.run_esco_source(s, "esco")


@pytest.fixture
def client(engine, monkeypatch):
    monkeypatch.setitem(sources().get("esco").options, "max_failed_share", 1.0)
    with Session(engine) as s:
        esco.run_esco_source(s, "esco")
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_skills_api(client):
    r = client.get("/api/v1/occupations/2512/skills").json()
    assert r["total"] == 3 and [i["skill_code"] for i in r["items"]] == ["prog", "test", "uml"]
    assert r["items"][0]["skill_type_label"] == "Conocimiento" and r["weight_note"]
    assert client.get("/api/v1/occupations/2512/skills", params={"skill_type": "skill"}).json()["total"] == 1
    found = client.get("/api/v1/skills", params={"q": "program"}).json()
    assert found[0]["skill_code"] == "prog" and found[0]["occupations"] == 1
    detail = client.get("/api/v1/skills/prog").json()
    assert detail["used_by"][0]["occupation"]["occupation_code"] == "2512"
    assert client.get("/api/v1/skills/nope").status_code == 404
    assert client.get("/api/v1/occupations/nope/skills").status_code == 404
