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
    # the hierarchy step has its own test; here it must not reach the ESCO API
    monkeypatch.setattr(esco, "run_esco_hierarchy", lambda session, source: (0, 0, []))
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
    with Session(engine) as s:  # ESCO category: essential in any of the group's occupations wins
        rel = {sk: r for sk, r in s.execute(select(OccupationSkill.skill_code, OccupationSkill.relation)
                                             .where(OccupationSkill.country_iso3 == "ARG",
                                                    OccupationSkill.occupation_code == "2512")).all()}
    assert rel == {"prog": "essential", "test": "essential", "uml": "optional"}
    with Session(engine) as s:  # which ESCO occupations of the group use each skill, and how
        via = s.scalar(select(OccupationSkill.via).where(OccupationSkill.country_iso3 == "ARG",
                                                         OccupationSkill.occupation_code == "2512",
                                                         OccupationSkill.skill_code == "uml"))
    assert via and {v["relation"] for v in via} == {"optional"} and len(via) == 1
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
    # palabras en cualquier orden, sin tildes y solo al comienzo de una palabra
    codes = lambda q: [i["skill_code"] for i in client.get("/api/v1/skills", params={"q": q}).json()]  # noqa: E731
    assert codes("programacion") == ["prog"] and codes("software probar") == ["test"]
    assert codes("gramacion") == [] and codes("probar uml") == []
    detail = client.get("/api/v1/skills/prog").json()
    assert detail["used_by"][0]["occupation"]["occupation_code"] == "2512"
    assert client.get("/api/v1/skills/nope").status_code == 404
    assert client.get("/api/v1/occupations/nope/skills").status_code == 404


def test_esco_hierarchy_levels():
    from app.skills.esco_hierarchy import concept_level

    assert [concept_level(c) for c in ("S", "S2", "S2.2", "S2.2.1", "A1.10.0")] == [0, 1, 2, 3, 3]
    assert [concept_level(c) for c in ("04", "041", "0412")] == [1, 2, 3]  # CINE-F fields


def test_esco_hierarchy_descriptions_groups_and_broken_records(engine, monkeypatch):
    import httpx

    from app.models import SkillGroup
    from app.skills import esco_hierarchy

    S = "http://data.europa.eu/esco/skill/"
    skills = {S + "prog": {"description": {"en": {"literal": "Write code."}, "es": {"literal": "Escribir código."}},
                           "_links": {"broaderHierarchyConcept": [{"uri": S + "S5.1.1", "title": "programar"}]}},
              S + "fin": {"description": {"en": {"literal": "Finance basics."}},
                          "_links": {"broaderHierarchyConcept": [{"uri": S + "S2.2.1", "title": "informes financieros"}]}}}
    concepts = {S + "S5.1.1": {"title": "programar", "_links": {"broaderConcept": [{"uri": S + "S5.1"}]}},
                S + "S5.1": {"title": "usar computadoras", "_links": {"broaderConcept": [{"uri": S + "S5"}]}},
                S + "S5": {"title": "trabajar con computadoras", "_links": {}}}
    broken = {S + "bad", S + "S2.2.1"}  # ESCO answers 500 for any batch that includes these

    async def fake(client, url, params=None, headers=None):
        uris = [v for k, v in params if k == "uris"]
        request = httpx.Request("GET", url)
        if broken & set(uris):
            raise httpx.HTTPStatusError("500", request=request, response=httpx.Response(500, request=request))
        table = skills if url.endswith("/skill") else concepts
        return httpx.Response(200, request=request, json={"_embedded": {u: table[u] for u in uris if u in table}})

    monkeypatch.setattr(esco_hierarchy, "get_with_retry", fake)
    with Session(engine) as s:
        s.add_all([Skill(skill_code="prog", name="programar", esco_uri=S + "prog"),
                   Skill(skill_code="fin", name="finanzas", esco_uri=S + "fin"),
                   Skill(skill_code="bad", name="roto", esco_uri=S + "bad")])
        s.commit()
        with_group, groups, failed = esco_hierarchy.run_esco_hierarchy(s, "esco")
        s.commit()
        prog, fin, bad = s.get(Skill, "prog"), s.get(Skill, "fin"), s.get(Skill, "bad")
        assert (prog.description, prog.group_code) == ("Escribir código.", "S5.1.1")  # Spanish first
        assert (fin.description, fin.group_code) == ("Finance basics.", "S2.2.1")  # English fallback
        assert bad.group_code is None and with_group == 2
        assert sorted(failed) == ["S2.2.1", "bad"]  # only the broken records are skipped
        assert s.get(SkillGroup, "S5.1.1").parent_code == "S5.1" and s.get(SkillGroup, "S5").level == 1
        assert s.get(SkillGroup, "S2.2.1").name == "informes financieros"  # named as its skills link it


def test_descriptions_spanish_first_then_translation_while_original_matches():
    from app.skills.esco_hierarchy import ORIGIN_ESCO, ORIGIN_TRANSLATION, describe

    conf = sources().get("esco")
    translations = {"0541": {"en": "Mathematics is the study of abstract deductive systems.",
                             "es": "Las matemáticas son el estudio de los sistemas deductivos abstractos."}}
    both = {"es": {"literal": "Texto de ESCO."}, "en": {"literal": "ESCO text."}}
    assert describe(both, "0541", conf, translations) == ("Texto de ESCO.", "ESCO text.", ORIGIN_ESCO)
    english = {"en": {"literal": "Mathematics is the study of abstract deductive systems."}}
    assert describe(english, "0541", conf, translations) == (
        "Las matemáticas son el estudio de los sistemas deductivos abstractos.",
        "Mathematics is the study of abstract deductive systems.", ORIGIN_TRANSLATION)
    # ESCO changed its English text: the old translation no longer applies, English is shown
    changed = {"en": {"literal": "Mathematics is the study of numbers."}}
    assert describe(changed, "0541", conf, translations) == (
        "Mathematics is the study of numbers.", "Mathematics is the study of numbers.", None)


def test_translation_file_keeps_esco_original_next_to_each_translation():
    import yaml

    from app.core.config import settings

    data = yaml.safe_load((settings.config_dir / sources().get("esco").options["translations_file"]).read_text())
    assert data["reviewed"] is False and data["groups"]
    assert all(g["en"].strip() and g["es"].strip() for g in data["groups"].values())


def test_search_tokens_and_pattern():
    import re

    from app.core.search import stem, token_pattern, tokens

    assert tokens("  Asesorar, ganado!  ") == ["asesorar", "ganado"]
    assert tokens("Nutrición") == ["nutricion"]
    pat = re.compile(token_pattern("nutricion"), re.I)
    assert pat.search("asesorar sobre nutrición") and pat.search("(Nutrición)") and not pat.search("desnutrición")

    # plural and gender: the root of each word is searched
    assert stem("enfermera") == "enfermer" and stem("desarrolladores") == "desarrollador"
    assert stem("medicos") == "medic" and stem("contador") == "contador" and stem("casa") == "casa"
    for word, name in (("enfermera", "Profesional de enfermería"), ("desarrolladores", "Desarrollador/a de software"),
                       ("abogadas", "Abogados"), ("medicos", "Médicos generales")):
        assert re.compile(token_pattern(stem(word)), re.I).search(name), (word, name)
