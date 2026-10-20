"""Skill gaps: supply from graduates via the career crosswalk, demand from employment."""
import io
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.recompute import refresh_skill_gaps
from app.analytics.skill_gaps_run import crosswalk_codes, crosswalk_levels
from app.core.config_files import catalog
from app.core.database import get_session
from app.datasets.profiles import normalize_text, profiles
from app.datasets.reader import read_dataset
from app.ingestion.pipeline import upsert_observations
from app.main import app
from app.models import (
    Base,
    Country,
    Graduate,
    Indicator,
    Methodology,
    OccupationSkill,
    Skill,
    SkillGap,
    Source,
)
from tests.conftest import sqlite_tables

FETCHED = datetime(2026, 10, 17, tzinfo=UTC)


def _emp(occ, year, value):
    return dict(indicator_code="employment", country_iso3="CHL", sector_code=None,
                occupation_code=occ, period_start=date(year, 1, 1), period_end=date(year, 12, 31),
                frequency="A", value=value, unit="thousands_persons", data_type="observed",
                source_id=1, run_id=None, source_updated_at=None, fetched_at=FETCHED)


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng, tables=sqlite_tables())
    with Session(eng) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en)
                   for c in catalog().countries])
        s.add(Source(source_id=1, source_code="simel_chile", name="SIMEL", source_kind="api"))
        s.add(Source(source_id=2, source_code="mifuturo_chile", name="Mi Futuro", source_kind="dataset"))
        s.add(Indicator(indicator_code="employment", name="Ocupados", unit="thousands_persons",
                        domain="labor"))
        # demand: nurses (2221) +10%/yr, accountants (2411) flat
        upsert_observations(s, [_emp("2221", 2022, 100), _emp("2221", 2025, 133.1),
                                _emp("2411", 2022, 100), _emp("2411", 2025, 100)])
        # supply: "Enfermería" -> 2221 grows 0%/yr; "Contador Auditor" -> 2411 grows +10%/yr
        for career, values in {"Enfermería": (1000, 1000), "Contador Auditor": (500, 665.5)}.items():
            for year, v in zip((2022, 2025), values):
                s.add(Graduate(country_iso3="CHL", career_key=normalize_text(career), career=career,
                               level="Pregrado", year=year, graduates=v, source_id=2))
        s.add_all([Skill(skill_code="care", name="cuidar pacientes", skill_type="skill"),
                   Skill(skill_code="audit", name="auditar cuentas", skill_type="skill"),
                   Skill(skill_code="talk", name="comunicarse", skill_type="skill")])
        for country in ("ARG", "URY", "CHL"):
            s.add_all([OccupationSkill(occupation_code="2221", skill_code="care", country_iso3=country, weight=1.0),
                       OccupationSkill(occupation_code="2411", skill_code="audit", country_iso3=country, weight=1.0),
                       OccupationSkill(occupation_code="2221", skill_code="talk", country_iso3=country, weight=0.5),
                       OccupationSkill(occupation_code="2411", skill_code="talk", country_iso3=country, weight=0.5)])
        s.commit()
        refresh_skill_gaps(s)
        s.commit()
    return eng


def test_gap_is_demand_minus_supply(engine):
    with Session(engine) as s:
        g = {x.skill_code: x for x in s.scalars(select(SkillGap).where(SkillGap.country_iso3 == "CHL"))}
    assert g["care"].demand_growth == pytest.approx(0.10) and g["care"].supply_growth == pytest.approx(0.0)
    assert g["care"].gap == pytest.approx(0.10) and g["care"].data_sufficiency == "full"
    assert g["audit"].gap == pytest.approx(-0.10)
    # shared skill: equal weights -> averages of both occupations
    assert g["talk"].demand_growth == pytest.approx(0.05) and g["talk"].supply_growth == pytest.approx(0.05)
    assert g["talk"].gap == pytest.approx(0.0) and g["talk"].occupations == 2
    from app.core.config_files import analytics_params

    threshold = analytics_params("skill_gaps")["emerging_growth"]
    assert g["care"].is_emerging == (g["care"].demand_growth > threshold)
    assert not g["audit"].is_emerging


def test_countries_without_supply_never_get_a_gap(engine):
    with Session(engine) as s:
        rows = s.scalars(select(SkillGap).where(SkillGap.country_iso3 != "CHL")).all()
    assert all(r.gap is None and r.data_sufficiency != "full" for r in rows)


def test_gaps_api_rankings(engine):
    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    try:
        c = TestClient(app)
        top = c.get("/api/v1/skills/gaps", params={"country": "CHL", "min_occupations": 1}).json()
        assert [i["skill"]["skill_code"] for i in top["items"]] == ["care", "talk", "audit"]
        assert top["crosswalk_reviewed"]["CHL"] is False and top["items"][0]["data_type"] == "calculated"
        bottom = c.get("/api/v1/skills/gaps", params={"country": "CHL", "view": "bottom",
                                                      "min_occupations": 1}).json()
        assert bottom["items"][0]["skill"]["skill_code"] == "audit"
        # default minimum (config) keeps only skills used by several occupations
        default = c.get("/api/v1/skills/gaps", params={"country": "CHL"}).json()
        assert default["min_occupations"] >= 2 and all(i["occupations"] >= 2 for i in default["items"])
        # no employment data for Argentina in this fixture: nothing to compare, no rows
        arg = c.get("/api/v1/skills/gaps", params={"country": "ARG", "view": "all"}).json()
        assert arg["full_total"] == 0 and all(i["gap"] is None for i in arg["items"])
    finally:
        app.dependency_overrides.clear()


def test_aggregate_reader_adds_up_program_rows(tmp_path):
    prof = profiles()["mifuturo_titulados"]
    wb = Workbook()
    ws = wb.active
    ws.title = prof.file.sheet
    ws.append(prof.expected.headers)
    idx = {h: i for i, h in enumerate(prof.expected.headers)}

    def row(year, career, total, level="Pregrado"):
        r = [None] * len(prof.expected.headers)
        r[idx["AÑO"]], r[idx["TOTAL TITULACIONES"]] = f"TIT_{year}", total
        r[idx["ÁREA CARRERA GENÉRICA"]], r[idx["NIVEL GLOBAL"]] = career, level
        r[idx["CINE-F_13 ÁREA"]], r[idx["CINE-F_13 SUBAREA"]] = "Salud y Bienestar", "Salud"
        return r

    for year in range(2007, 2026):
        ws.append(row(year, "Enfermería", 10))
        ws.append(row(year, "Enfermería", 5))   # second program of the same career
        ws.append(row(year, "Enfermería", 3, level="Posgrado"))
    path = tmp_path / "titulados.xlsx"
    buf = io.BytesIO()
    wb.save(buf)
    path.write_bytes(buf.getvalue())
    r = read_dataset(path, prof)
    assert r.ok, r.errors
    rows = {(x["year"], x["level"]): x["value"] for x in r.rows}
    assert rows[(2025, "Pregrado")] == 15 and rows[(2025, "Posgrado")] == 3
    assert r.periods[0] == "2007" and r.periods[-1] == "2025"
    ws.cell(row=1, column=1, value="AÑO DE TITULACIÓN")  # renamed column: blocked
    wb.save(buf := io.BytesIO())
    path.write_bytes(buf.getvalue())
    assert not read_dataset(path, prof).ok


def test_crosswalk_review_json_and_csv(engine):
    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    try:
        c = TestClient(app)
        r = c.get("/api/v1/graduates/crosswalk", params={"country": "CHL"}).json()
        assert r["reviewed"] is False and r["careers"] == r["mapped"] + r["generic"]
        top = r["items"][0]  # most graduates first: Enfermería (1000) before Contador Auditor
        assert top["career"] == "Enfermería" and top["graduates"] == 1000
        occ = top["occupations"][0]
        assert occ["occupation_code"] == "2221" and occ["share"] == 1.0
        assert [h["code"] for h in occ["hierarchy"]] == ["2", "22", "222", "2221"]
        assert occ["hierarchy"][0]["name"] == "Profesionales científicos e intelectuales"
        assert any(i["is_generic"] and not i["occupations"] for i in r["items"])
        csv_text = c.get("/api/v1/graduates/crosswalk",
                         params={"country": "CHL", "format": "csv"}).text
        header = csv_text.lstrip("﻿").splitlines()[0]
        assert header.startswith("carrera,") and "gran_grupo" in header
        assert c.get("/api/v1/graduates/crosswalk", params={"country": "BRA"}).status_code == 404  # no crosswalk
    finally:
        app.dependency_overrides.clear()


def test_hierarchy_reads_the_code_left_to_right():
    names = dict(catalog().hierarchy("2132"))
    assert names["2"] == "Profesionales científicos e intelectuales"
    assert names["21"] == "Profesionales de las ciencias y de la ingeniería"
    assert names["213"] == "Profesionales en ciencias biológicas"
    assert catalog().hierarchy("3142")[0] == ("3", "Técnicos y profesionales de nivel medio")
    # every occupation of the universe has names for all its levels
    assert all(name for o in catalog().occupations for _, name in catalog().hierarchy(o.occupation_code))


def test_crosswalk_codes_per_level():
    assert crosswalk_levels({"levels": ["Grado", "Pregrado"]}) == ["Grado", "Pregrado"]
    assert crosswalk_levels({"level": "Pregrado"}) == ["Pregrado"]
    entry = {"Pregrado": [3512], "*": [2511, 2512]}
    assert crosswalk_codes(entry, "Pregrado") == ["3512"]
    assert crosswalk_codes(entry, "Grado") == ["2511", "2512"]
    assert crosswalk_codes([2611], "Grado") == ["2611"]
    assert crosswalk_codes([], "Grado") == [] and crosswalk_codes(None, "Grado") == []


def test_superseded_results_are_pruned_but_methodologies_kept(engine, monkeypatch):
    from app.core.config_files import analytics

    with Session(engine) as s:
        old = Methodology(methodology_type="skill_gap", version="0.1", params={}, params_hash="old",
                          created_at=datetime.now(UTC))
        s.add(old)
        s.flush()
        s.add(SkillGap(country_iso3="CHL", skill_code="care", year=2020, is_emerging=False,
                       data_sufficiency="none", demand_coverage=0, supply_coverage=0,
                       occupations=1, details={}, methodology_id=old.methodology_id,
                       computed_at=datetime.now(UTC)))
        s.commit()
        monkeypatch.setitem(analytics()["recompute"], "keep_superseded_results", True)
        refresh_skill_gaps(s)
        assert s.scalar(select(func.count()).where(SkillGap.methodology_id == old.methodology_id)) == 1
        monkeypatch.setitem(analytics()["recompute"], "keep_superseded_results", False)
        refresh_skill_gaps(s)
        s.commit()
        assert s.scalar(select(func.count()).where(SkillGap.methodology_id == old.methodology_id)) == 0
        assert s.get(Methodology, old.methodology_id) is not None  # what that version used stays
        assert s.scalar(select(func.count()).select_from(SkillGap)) > 0  # current results stay
