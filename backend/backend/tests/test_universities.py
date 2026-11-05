from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config_files import analytics_params, sources
from app.core.database import get_session
from app.datasets import universities
from app.datasets.ingest import DatasetError
from app.datasets.universities import (
    apply_names,
    load_universities,
    normalized_name,
    ranking_rows,
    run_universities_source,
    tidy_yearbook_table,
    to_number,
    university_names,
)
from app.jobs.scheduler import scheduled_sources
from app.main import app
from app.models import (
    Alert,
    Base,
    Country,
    DataRevision,
    DatasetFile,
    FactInstitucionesEgresados,
    IngestionRun,
    RankingUniversidadesNacional,
    RankingUniversidadesRegional,
    Source,
)

CONF = analytics_params("universities")


def _raw(name, country, year, value, source="anuario_diu_argentina", kind="universidad"):
    return {"pais": country, "publicado": name, "tipo_gestion": "publica", "tipo_institucion": kind,
            "anio": year, "graduados": value, "fuente_id": source, "es_observado": True}


RAW = [
    _raw("Buenos Aires", "ARG", 2023, 100.0),
    _raw("Buenos Aires", "ARG", 2024, 110.0),
    _raw("Salvador (4)", "ARG", 2024, 50.0),
    _raw("ITBA (8)", "ARG", 2024, 900.0, kind="instituto universitario"),
    _raw("UNIVERSIDAD ANDRES BELLO", "CHL", 2024, 90.0, "mifuturo_chile"),
    _raw("UNIVERSIDAD ANDRES BELLO", "CHL", 2025, 95.0, "mifuturo_chile"),
    _raw("Universidad de la República (UdelaR)", "URY", 2024, 70.0, "udelar_planeamiento"),
]


@pytest.fixture
def engine():
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=[t.__table__ for t in (
        Country, Source, IngestionRun, DataRevision, DatasetFile, Alert, FactInstitucionesEgresados,
        RankingUniversidadesNacional, RankingUniversidadesRegional)])
    with Session(engine) as s:
        s.add(Source(source_code="anuario_diu_argentina", name="DIU", source_kind="dataset"))
        s.add(Source(source_code="universidades_egresados", name="U", source_kind="dataset"))
        s.commit()
    return engine


def _load(session, raw=RAW, run_id=None):
    rows, _ = apply_names(raw, CONF)
    national, regional = ranking_rows(rows, CONF)
    return load_universities(session, rows, national, regional, run_id)


def test_missing_markers_are_not_zero():
    assert to_number("s/d", CONF) is None and to_number("-", CONF) is None
    assert to_number(0, CONF) == 0 and to_number("1.475", CONF) == 1475


def test_yearbook_rows_keep_kind_and_skip_totals():
    out = tidy_yearbook_table([
        [None, 2021, 2022],
        ["Total Universidades Nacionales ", 20, 30],
        ["Buenos Aires", 20, 30],
        ["Total Institutos Universitarios Nacionales", 10, 10],
        ["Patagónico de las Artes", "-", 10],
    ], "publica", CONF)
    assert {r["publicado"] for r in out} == {"Buenos Aires", "Patagónico de las Artes"}
    institute = [r for r in out if r["publicado"] == "Patagónico de las Artes"]
    assert [r["anio"] for r in institute] == [2022]
    assert institute[0]["tipo_institucion"] == "instituto universitario"


def test_names_remove_footnotes_unless_the_marked_form_is_listed():
    assert normalized_name("ARG", "Salvador (4)", CONF) == "Universidad del Salvador"
    assert normalized_name("ARG", "DD. HH. Madres de Plaza de Mayo (3) (5)", CONF) == \
        normalized_name("ARG", "Madres de Plaza de Mayo (3)", CONF)
    assert normalized_name("ARG", "Madres de Plaza de Mayo (2)", CONF) == \
        "Universidad Popular Madres de Plaza de Mayo"
    assert normalized_name("ARG", "No existe", CONF) is None


def test_names_file_has_no_empty_names_and_review_names_exist():
    names = university_names()
    listed = {n for c in ("ARG", "CHL", "URY") for n in names[c].values()}
    assert all(listed) and set(names["review"]) <= listed


def test_published_forms_of_one_institution_are_added_up():
    rows, missing = apply_names([
        _raw("UNIVERSIDAD DEL PACIFICO", "CHL", 2020, 10.0, "mifuturo_chile"),
        _raw("UNIVERSIDAD DEL PACIFICO (CARRERA EN CONVENIO UTEM)", "CHL", 2020, 5.0, "mifuturo_chile"),
        _raw("Nueva Universidad", "ARG", 2024, 1.0),
    ], CONF)
    pacifico = next(r for r in rows if r["pais"] == "CHL")
    assert pacifico["institucion"] == "Universidad del Pacífico" and pacifico["graduados"] == 15.0
    assert missing == ["ARG: Nueva Universidad"]
    assert any(r["institucion"] == "Nueva Universidad" for r in rows)  # kept as published


def test_regional_ranking_uses_the_latest_shared_year_and_only_universities():
    rows, _ = apply_names(RAW, CONF)
    national, regional = ranking_rows(rows, CONF)
    assert {r["anio_evaluado"] for r in regional} == {"2024"}
    assert [r["graduados"] for r in regional] == [110.0, 90.0, 70.0, 50.0]
    chile = next(r for r in national if r["pais"] == "CHL")
    assert chile["anio_evaluado"] == "2025" and chile["total_instituciones_pais"] == 1


def test_load_is_idempotent_and_logs_what_changes(engine):
    with Session(engine) as s:
        assert _load(s) == 0
        s.commit()
        assert s.scalar(select(Source.source_id).where(
            Source.source_code == "udelar_planeamiento")) is not None
        assert _load(s) == 0
        s.commit()
        revised = [{**r, "graduados": 120.0} if r["publicado"] == "Buenos Aires" and r["anio"] == 2024
                   else r for r in RAW if r["publicado"] != "Salvador (4)"]
        assert _load(s, revised) == 2
        s.commit()
        logged = {r.record_key["institucion"]: (r.change, r.old_value, r.new_value)
                  for r in s.scalars(select(DataRevision)).all()}
        assert logged == {"Universidad de Buenos Aires": ("revised", 110.0, 120.0),
                          "Universidad del Salvador": ("removed", 50.0, None)}


def _run(session):
    run = IngestionRun(source_id=session.scalar(select(Source.source_id).where(
        Source.source_code == "universidades_egresados")), started_at=datetime.now(UTC),
        status="running", triggered_by="test")
    session.add(run)
    session.flush()
    return run


def _offline(monkeypatch, tmp_path, links, controls=()):
    monkeypatch.setattr(universities, "_official_links", lambda conf: links)
    monkeypatch.setattr(universities, "download_sync", lambda url, *a, **k: url.encode())
    monkeypatch.setattr(universities, "read_official_files", lambda files, conf: (RAW, list(controls)))
    conf = universities.app_config().datasets
    monkeypatch.setattr(type(conf), "path", lambda self, d: tmp_path)


LINKS = [("arg_latest", 100, "https://www.argentina.gob.ar/a.zip", "2024"),
         ("udelar", 100, "https://planeamiento.udelar.edu.uy/b.ods", None)]


def test_run_loads_then_skips_until_a_link_changes(engine, monkeypatch, tmp_path):
    _offline(monkeypatch, tmp_path, LINKS)
    with Session(engine) as s:
        loaded, warnings = run_universities_source(s, "universidades_egresados", _run(s))
        s.commit()
        assert loaded == 7 and warnings == []
        assert run_universities_source(s, "universidades_egresados", _run(s)) == (0, [])
        s.commit()
        assert {d.status for d in s.scalars(select(DatasetFile)).all()} == {"loaded"}

        _offline(monkeypatch, tmp_path, [LINKS[0], ("udelar", 100, "https://planeamiento.udelar.edu.uy/c.ods", None)])
        assert run_universities_source(s, "universidades_egresados", _run(s))[0] == 7
        s.commit()
        statuses = sorted(d.status for d in s.scalars(select(DatasetFile)).all())
        assert statuses == ["loaded", "loaded", "replaced", "replaced"]


def test_totals_that_do_not_match_stop_the_load(engine, monkeypatch, tmp_path):
    bad = {"control": "x", "anio": 2024, "valor": 1, "esperado": 2, "resultado": CONF["control_pending"]}
    _offline(monkeypatch, tmp_path, LINKS, [bad])
    with Session(engine) as s:
        with pytest.raises(DatasetError):
            run_universities_source(s, "universidades_egresados", _run(s))
        s.commit()
        assert s.scalars(select(FactInstitucionesEgresados)).first() is None
        assert {d.status for d in s.scalars(select(DatasetFile)).all()} == {"format_changed"}
        assert s.scalars(select(Alert)).first().alert_type == "source_format_changed"


def test_source_is_scheduled_and_every_input_is_official():
    assert "universidades_egresados" in dict(scheduled_sources())
    assert sources().get("universidades_egresados").connector == "universities"
    assert set(CONF["inputs"]) == {"arg_latest", "arg_history", "chl", "ury", "udelar"}


def test_universities_api(engine):
    with Session(engine) as s:
        _load(s)
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    try:
        client = TestClient(app)
        arg = client.get("/api/v1/graduates/universities", params={"country": "arg", "year": 2024}).json()
        assert arg["items"][0]["institucion"] == "Instituto Tecnológico de Buenos Aires"
        assert arg["items"][0]["nivel"] == "Pregrado y grado" and arg["nota"]
        regional = client.get("/api/v1/graduates/universities/ranking").json()
        assert regional["items"][0]["institucion"] == "Universidad de Buenos Aires"
        assert regional["items"][1]["posicion"] == 2
        national = client.get("/api/v1/graduates/universities/ranking",
                              params={"alcance": "nacional", "country": "URY"}).json()
        assert [i["institucion"] for i in national["items"]] == ["Universidad de la República (Udelar)"]
    finally:
        app.dependency_overrides.clear()
