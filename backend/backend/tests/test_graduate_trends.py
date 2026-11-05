import io
import zipfile
from datetime import UTC, datetime

import openpyxl
import pytest
import yaml
from fastapi.testclient import TestClient
from openpyxl.styles import Font
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.graduate_trends_run import (
    CareerSeries,
    GraduateRow,
    all_series,
    analyze,
    career_institutions,
    career_name,
    career_sectors,
    career_series,
    recompute_graduate_trends,
)
from app.core.config import settings
from app.core.config_files import analytics_params, catalog
from app.core.database import get_session
from app.datasets.ingest import DatasetError
from app.datasets.profiles import normalize_text
from app.datasets.tracked_careers import (
    argentine_disciplines,
    load_tracked,
    matching_topic,
    program_totals,
    read_argentina_yearbook,
    read_uruguay_yearbook,
    run_tracked_careers_source,
    tracked_definitions,
)
from app.main import app
from app.models import (
    Alert,
    Base,
    Country,
    DataRevision,
    DatasetFile,
    FactEgresados,
    Graduate,
    GraduateProjection,
    GraduateTrend,
    IngestionRun,
    Source,
)

CONF = analytics_params("graduate_trends")
CTI, DIU = "indicadores_cti_argentina", "anuario_diu_argentina"


def _row(key, level, year, value, source=CTI, country="ARG", name=None):
    return GraduateRow(country, key, name or key.capitalize(), level, year, value, source)


def _one(rows):
    series = career_series(rows, CONF)
    assert len(series) == 1
    return series[0]


def test_postgraduate_degrees_are_not_counted():
    series = _one([_row("medicina", "Grado", 2023, 100.0), _row("medicina", "Pregrado", 2023, 10.0),
                   _row("medicina", "Posgrado", 2023, 90.0)])
    assert series.by_year == {2023: 110.0}


def test_each_year_uses_one_source_and_the_later_source_extends_the_series():
    series = _one([_row("medicina", "Grado", 2023, 100.0),
                   _row("medicina", "Pregrado y grado", 2023, 999.0, DIU),
                   _row("medicina", "Pregrado y grado", 2024, 120.0, DIU)])
    assert series.by_year == {2023: 100.0, 2024: 120.0} and series.last_year == 2024


def test_argentine_yearbooks_win_over_cti_except_the_excluded_year(session):
    session.add(Country(iso3="ARG", name_es="Argentina", name_en="Argentina"))
    session.add(Source(source_id=3, source_code=CTI, name="C", source_kind="dataset"))
    session.add_all([Graduate(country_iso3="ARG", career_key="medicina", career="Medicina", level="Grado",
                              year=y, graduates=v, source_id=3) for y, v in ((2015, 10.0), (2016, 80.0), (2019, 90.0))])
    generic = TRACKED["institution_granularity"]
    for year, value, institution in ((2015, 1.0, "A"), (2016, 60.0, "A"), (2016, 40.0, "B")):
        session.add(FactEgresados(**{**_tracked_row(year, value, "Pregrado y grado", "Medicina", institution),
                                     "pais": "ARG", "nivel_granularidad": generic}))
    session.commit()
    series = next(s for s in all_series(session) if s.pais == "argentina")
    assert series.by_year == {2015: 10.0, 2016: 100.0, 2019: 90.0}


def test_unlisted_sources_and_skipped_careers_are_ignored():
    assert career_series([_row("sin disciplina", "Grado", 2023, 5.0)], CONF) == []
    assert career_series([_row("medicina", "Grado", 2023, 5.0, "manual_upload")], CONF) == []


def test_footnote_marks_do_not_split_a_career():
    series = _one([_row("energia*", "Pregrado", 2023, 5.0, "mifuturo_chile", "CHL", "Energía*"),
                   _row("energia", "Pregrado", 2024, 7.0, "mifuturo_chile", "CHL", "Energía")])
    assert series.nombre == "Energía" and series.by_year == {2023: 5.0, 2024: 7.0}
    assert series.pais == "chile"


def _uruguay(name, year, value):
    return GraduateRow("URY", "ignored", name, "Grado", year, value, "mec_uruguay")


def test_uruguay_renames_join_one_series():
    series = _one([_uruguay("Doctor en Derecho y Ciencias Sociales", 2023, 253.0),
                   _uruguay("Abogacía", 2023, 47.0), _uruguay("Abogacía", 2024, 339.0)])
    assert series.nombre == "Abogacía" and series.by_year == {2023: 300.0, 2024: 339.0}
    assert series.pais == "uruguay"


def test_uruguay_rules_remove_campus_and_titles_before_matching():
    for published, final in [
        ("Licenciado en Psicología", "Licenciatura en Psicología"),
        ("Lic. en Economía", "Licenciatura en Economía"),
        ("Licenciatura en Gestión Cultural (Montevideo)", "Licenciatura en Gestión Cultural"),
        ("Tecnólogo Químico (DGETP - UTU-UTEC)", "Tecnólogo Químico"),
        ("Ingeniero Civil", "Ingeniería Civil"),
        ("Licenciada en Obstetricia (Paysandú - Entre Ríos)", "Obstetricia"),
        ("Ingeniería en Mecatrónica*", "Ingeniería en Mecatrónica"),
        ("Técnico en Hemoterapia", "Tecnicatura en Hemoterapia"),
    ]:
        assert career_name(published, CONF["countries"]["URY"], CONF) == final


def test_different_careers_with_similar_names_stay_apart():
    names = {career_name(n, CONF["countries"]["URY"], CONF) for n in (
        "Licenciatura en Comunicación", "Licenciatura en Ciencias de la Comunicación",
        "Contador Público", "Licenciatura en Administración")}
    assert len(names) == 4


def test_names_file_is_consistent():
    with (settings.config_dir / CONF["countries"]["URY"]["names_file"]).open(encoding="utf-8") as f:
        table = yaml.safe_load(f)
    forms = [form for group in table["equivalencias"].values() for form in group]
    assert len(forms) == len(set(forms)) and all(form == normalize_text(form) for form in forms)
    assert set(table["review"]) <= set(table["equivalencias"])


def test_other_countries_keep_their_published_names():
    assert career_name("Ingeniero Civil", CONF["countries"]["CHL"], CONF) == "Ingeniero Civil"


def _series(values, start=2005, last=None):
    by_year = {start + i: float(v) for i, v in enumerate(values)}
    return CareerSeries("chile", "a", by_year, last or max(by_year))


def test_growing_series_gets_projection_with_floor_at_zero():
    trend, projections = analyze(_series([10 + 5 * i for i in range(15)]))
    assert trend["tendencia"] == "growing" and trend["proyeccion"] == "generada"
    assert [p["anio"] for p in projections] == [2020, 2021, 2022, 2023]
    assert all(p["limite_inferior"] >= 0 for p in projections)


def test_short_series_has_trend_but_no_projection():
    trend, projections = analyze(_series([10, 12, 15, 19, 24], start=2021))
    assert trend["tendencia"] == "growing" and trend["proyeccion"].startswith("historia_insuficiente")
    assert projections == []


def test_years_before_the_first_graduates_are_not_data():
    trend, _ = analyze(_series([0, 0, 10, 12, 15, 19, 24], start=2019))
    assert trend["anio_desde"] == 2021 and trend["n_anios_serie"] == 5 and not trend["tiene_huecos"]


def test_career_that_stopped_has_gaps_up_to_the_latest_year():
    by_year = {y: 50.0 for y in range(2010, 2021)}
    trend, projections = analyze(CareerSeries("chile", "a", by_year, 2025))
    assert trend["tiene_huecos"] and trend["proyeccion"] == "con_huecos"
    assert trend["tendencia"] == "insufficient_data" and trend["anio_hasta"] == 2025
    assert projections == []


def test_career_without_graduates_is_left_out():
    assert analyze(_series([0, 0, 0])) is None


@pytest.fixture
def session():
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=[t.__table__ for t in (
        Country, Source, IngestionRun, DatasetFile, DataRevision, Graduate, GraduateTrend,
        GraduateProjection, FactEgresados, Alert)])
    with Session(engine) as s:
        s.add(Country(iso3="CHL", name_es="Chile", name_en="Chile"))
        s.add(Source(source_id=1, source_code="mifuturo_chile", name="M", source_kind="dataset"))
        s.commit()
        yield s


def _graduate(year, value):
    return Graduate(country_iso3="CHL", career_key="enfermeria", career="Enfermería", level="Pregrado",
                    year=year, graduates=value, source_id=1)


def test_recalculation_replaces_what_was_stored(session):
    session.add(GraduateTrend(pais="chile", nombre="ciberseguridad", anio_desde=2019, anio_hasta=2025,
                              n_anios_serie=7, ventana_anios=5, graduados_inicio_ventana=1,
                              graduados_ultimo=2, tendencia="growing", tiene_huecos=False,
                              proyeccion="x"))
    session.add_all([_graduate(y, 100.0 + y - 2007) for y in range(2007, 2026)])
    session.commit()
    assert recompute_graduate_trends(session) == 1
    trend = session.scalars(select(GraduateTrend)).one()
    assert (trend.pais, trend.nombre, trend.graduados_ultimo) == ("chile", "Enfermería", 118)
    years = [p.anio for p in session.scalars(select(GraduateProjection)).all()]
    assert sorted(years) == [2026, 2027, 2028, 2029]


TRACKED = analytics_params("tracked_careers")
CAREERS, _ = tracked_definitions(TRACKED)


def _topic(program):
    found = matching_topic(program, CAREERS)
    return found["nombre"] if found else None


def test_patterns_find_programs_and_avoid_lookalikes():
    assert _topic("DIPLOMADO EN INTELIGENCIA ARTIFICIAL") == "Inteligencia artificial"
    assert _topic("Ingeniería en Ciberseguridad") == "Ciberseguridad"
    assert _topic("TECNICO EN SEGURIDAD PRIVADA") is None
    assert _topic("INGENIERIA EN MINAS") == "Minería y litio"
    assert _topic("EXAMINADOR DE MINAS TERRESTRES") is None


def test_a_program_gets_only_the_first_topic_that_matches():
    assert _topic("DIPLOMADO EN DISEÑO UX/UI/AGILE") == "Diseño UX/UI"
    assert _topic("TECNICO EN ENERGIAS RENOVABLES Y EFICIENCIA ENERGETICA") == "Energías renovables"


def test_tracked_definitions_are_unique_and_have_a_catalog_sector():
    assert len({c["id"] for c in CAREERS}) == len({c["nombre"] for c in CAREERS}) == len(CAREERS)
    assert {c["sector"] for c in CAREERS} <= {s.sector_code for s in catalog().sectors}


UDP = "UNIVERSIDAD DIEGO PORTALES"


def test_totals_keep_the_original_name_per_institution_level_and_year():
    rows = program_totals([
        ("TIT_2024", 10, "DIPLOMADO EN  INTELIGENCIA ARTIFICIAL", "Postítulo", "Otros", UDP),
        ("TIT_2024", 5, "MAGISTER EN INTELIGENCIA ARTIFICIAL", "Posgrado", "Otros", UDP),
        ("TIT_2024", 7, "DIPLOMADO EN  INTELIGENCIA ARTIFICIAL", "Postítulo", "Otros", UDP),
        ("TIT_2024", 2, "DIPLOMADO EN  INTELIGENCIA ARTIFICIAL", "Postítulo", "Otros", "CFT ALFA"),
        ("TIT_2024", None, "DIPLOMADO EN  INTELIGENCIA ARTIFICIAL", "Postítulo", "Otros", UDP),
    ], CAREERS, TRACKED)
    assert {(r["carrera_objetivo"], r["institucion"], r["nivel"], r["valor"]) for r in rows} == {
        ("DIPLOMADO EN INTELIGENCIA ARTIFICIAL", "Universidad Diego Portales", "Postítulo", 17.0),
        ("DIPLOMADO EN INTELIGENCIA ARTIFICIAL", "CFT ALFA", "Postítulo", 2.0),
        ("MAGISTER EN INTELIGENCIA ARTIFICIAL", "Universidad Diego Portales", "Posgrado", 5.0)}
    assert {(r["anio"], r["carrera_id"], r["sector"]) for r in rows} == {(2024, "CHL_IA", "technology")}


def test_generic_careers_are_kept_per_institution_for_their_levels_only():
    rows = program_totals([
        ("TIT_2024", 3, "ENFERMERIA", "Pregrado", "Enfermería", UDP),
        ("TIT_2024", 4, "LICENCIATURA EN ENFERMERIA", "Pregrado", "Enfermería", UDP),
        ("TIT_2024", 9, "MAGISTER EN ENFERMERIA", "Posgrado", "Enfermería", UDP),
    ], CAREERS, TRACKED)
    assert [(r["carrera_objetivo"], r["institucion"], r["valor"], r["nivel_granularidad"]) for r in rows] == [
        ("Enfermería", "Universidad Diego Portales", 7.0, TRACKED["institution_granularity"])]


def _tracked_row(year, value, level="Postítulo", name="DIPLOMADO EN INTELIGENCIA ARTIFICIAL",
                 institution="Universidad Diego Portales"):
    return {"carrera_id": "CHL_IA", "carrera_objetivo": name, "sector": "technology", "nivel": level,
            "institucion": institution, "sexo": None, "anio": year, "valor": value, "pais": "CHL", "fuente_id": "mifuturo_chile",
            "nivel_granularidad": TRACKED["granularity"], "es_observado": True}


def test_programs_join_the_trends_under_their_original_name(session):
    session.add_all([FactEgresados(**_tracked_row(y, 10.0 * (y - 2018))) for y in range(2019, 2026)])
    session.add(FactEgresados(**_tracked_row(2025, 3.0, "Posgrado")))
    session.commit()
    recompute_graduate_trends(session)
    trend = session.scalars(select(GraduateTrend)).one()
    assert trend.es_seguimiento and trend.nombre == "DIPLOMADO EN INTELIGENCIA ARTIFICIAL"
    assert (trend.tema, trend.sector) == ("Inteligencia artificial", "technology")
    assert trend.graduados_ultimo == 73


def test_a_program_named_like_a_career_is_that_career(session):
    session.add(_graduate(2025, 50.0))
    session.add(FactEgresados(**_tracked_row(2025, 9.0, "Pregrado", "ENFERMERIA")))
    session.commit()
    recompute_graduate_trends(session)
    trend = session.scalars(select(GraduateTrend)).one()
    assert trend.nombre == "Enfermería" and not trend.es_seguimiento
    assert trend.graduados_ultimo == 50 and trend.tema == "Inteligencia artificial"


def test_sectors_come_from_the_official_field_not_from_loose_mappings():
    argentina = career_sectors()["ARG"]
    assert argentina["bioquimica y farmacia"] == "health"
    assert argentina["medicina"] == "health" and argentina["informatica"] == "technology"
    for career in ("demografia y geografia", "industrias", "ciencias de la informacion y de la comunicacion"):
        assert career not in argentina
    chile = career_sectors()["CHL"]
    assert chile["enfermeria"] == "health" and chile["ingenieria comercial"] == "knowledge_economy"


def test_sector_file_only_uses_catalog_sectors_and_real_fields():
    with (settings.config_dir / CONF["sector_file"]).open(encoding="utf-8") as f:
        table = yaml.safe_load(f)
    with (settings.config_dir / "reference/cine_f_2013.yaml").open(encoding="utf-8") as f:
        fields = set(yaml.safe_load(f)["detailed"])
    assert set(table["sectors"]) == {s.sector_code for s in catalog().sectors}
    listed = [field for group in table["sectors"].values() for field in group]
    assert len(listed) == len(set(listed)) and set(listed) <= fields and set(table["review"]) <= set(listed)


def test_tracked_load_logs_what_changes(session):
    ids = {"mifuturo_chile": 1}
    load_tracked(session, [_tracked_row(2024, 10.0), _tracked_row(2025, 20.0)], ids, None, TRACKED)
    session.commit()
    load_tracked(session, [_tracked_row(2024, 12.0)], ids, None, TRACKED)
    session.commit()
    logged = {r.record_key["anio"]: r.change for r in session.scalars(select(DataRevision)).all()}
    assert logged == {2024: "revised", 2025: "removed"}
    assert session.scalars(select(DataRevision)).first().record_key["institucion"] == "Universidad Diego Portales"
    assert [r.valor for r in session.scalars(select(FactEgresados)).all()] == [12.0]


LINK = ("chl", 100, "https://www.mifuturo.cl/t.xlsx", "2025")


def _run(session):
    run = IngestionRun(source_id=2, started_at=datetime.now(UTC), status="running", triggered_by="test")
    session.add(run)
    session.flush()
    return run


def _offline_tracked(monkeypatch, tmp_path):
    from app.datasets import tracked_careers as module

    monkeypatch.setattr(module, "_official_links", lambda conf: [LINK])
    monkeypatch.setattr(module, "download_sync", lambda *a, **k: b"x")
    conf = module.app_config().datasets
    monkeypatch.setattr(type(conf), "path", lambda self, d: tmp_path)
    return module


def test_tracked_run_skips_until_link_or_patterns_change(session, monkeypatch, tmp_path):
    session.add(Source(source_id=2, source_code="carreras_seguimiento", name="C", source_kind="dataset"))
    session.commit()
    module = _offline_tracked(monkeypatch, tmp_path)
    monkeypatch.setattr(module, "read_all", lambda *a: ([_tracked_row(2025, 5.0)], [], []))
    loaded, warnings = run_tracked_careers_source(session, "carreras_seguimiento", _run(session))
    session.commit()
    assert loaded == 1 and "Ciberseguridad" in warnings[0] and "Inteligencia" not in warnings[0]
    assert run_tracked_careers_source(session, "carreras_seguimiento", _run(session)) == (0, [])
    session.commit()
    monkeypatch.setattr(module, "tracked_definitions", lambda conf: (CAREERS, "otros-patrones"))
    assert run_tracked_careers_source(session, "carreras_seguimiento", _run(session))[0] == 1


def test_tracked_file_with_another_format_loads_nothing(session, monkeypatch, tmp_path):
    session.add(Source(source_id=2, source_code="carreras_seguimiento", name="C", source_kind="dataset"))
    session.commit()
    module = _offline_tracked(monkeypatch, tmp_path)

    def broken(*a):
        raise ValueError("falta una columna")

    monkeypatch.setattr(module, "read_all", broken)
    with pytest.raises(DatasetError):
        run_tracked_careers_source(session, "carreras_seguimiento", _run(session))
    session.commit()
    assert session.scalars(select(FactEgresados)).first() is None
    assert session.scalars(select(DatasetFile)).one().status == "format_changed"
    assert session.scalars(select(Alert)).one().alert_type == "source_format_changed"


def test_career_series_gives_observed_years_with_gaps_and_nothing_before_the_start(session):
    session.add_all([_graduate(2021, 0.0), _graduate(2022, 5.0), _graduate(2024, 7.0), _graduate(2025, 9.0)])
    session.commit()

    def override():
        yield session

    app.dependency_overrides[get_session] = override
    try:
        client = TestClient(app)
        series = client.get("/api/v1/graduates/series", params={"pais": "chile", "nombre": "Enfermería"}).json()
        assert series["puntos"] == [{"anio": 2022, "graduados": 5.0}, {"anio": 2023, "graduados": 0.0},
                                    {"anio": 2024, "graduados": 7.0}, {"anio": 2025, "graduados": 9.0}]
        same = client.get("/api/v1/graduates/series", params={"country": "CHL", "nombre": "Enfermería"}).json()
        assert same == series
        missing = client.get("/api/v1/graduates/series", params={"country": "CHL", "nombre": "No existe"})
        assert missing.status_code == 404 and "No existe" in missing.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_career_rows_name_the_largest_institution_and_how_many_there_are(session):
    session.add_all([FactEgresados(**_tracked_row(2025, 9.0)),
                     FactEgresados(**_tracked_row(2025, 4.0, institution="CFT ALFA")),
                     FactEgresados(**_tracked_row(2024, 90.0, institution="Otra"))])
    session.commit()
    recompute_graduate_trends(session)
    trend = session.scalars(select(GraduateTrend)).one()
    assert (trend.n_instituciones, trend.institucion_principal) == (2, "Universidad Diego Portales")


def _client(session):
    def override():
        yield session

    app.dependency_overrides[get_session] = override
    return TestClient(app)


def test_institutions_endpoint_gives_each_institution_and_year_totals(session):
    session.add_all([FactEgresados(**_tracked_row(2025, 9.0)), FactEgresados(**_tracked_row(2024, 1.0)),
                     FactEgresados(**_tracked_row(2025, 2.0, "Posgrado")),
                     FactEgresados(**_tracked_row(2025, 4.0, institution="CFT ALFA"))])
    session.commit()
    try:
        out = _client(session).get("/api/v1/graduates/institutions", params={
            "country": "CHL", "nombre": "DIPLOMADO EN INTELIGENCIA ARTIFICIAL"}).json()
        assert out["anios"] == [2024, 2025] and out["totales"] == {"2024": 1.0, "2025": 15.0}
        assert [(i["institucion"], i["total"]) for i in out["instituciones"]] == [
            ("Universidad Diego Portales", 12.0), ("CFT ALFA", 4.0)]
        assert out["instituciones"][0]["por_anio"] == {"2024": 1.0, "2025": 11.0}
    finally:
        app.dependency_overrides.clear()


def test_institution_filter_lists_institutions_and_gives_only_their_own_graduates(session):
    session.add_all([_graduate(y, 100.0) for y in (2024, 2025)])
    generic = TRACKED["institution_granularity"]
    session.add_all([
        FactEgresados(**{**_tracked_row(2025, 8.0, "Pregrado", "Enfermería"), "nivel_granularidad": generic}),
        FactEgresados(**{**_tracked_row(2024, 3.0, "Pregrado", "Enfermería"), "nivel_granularidad": generic}),
        FactEgresados(**{**_tracked_row(2025, 92.0, "Pregrado", "Enfermería", "CFT ALFA"), "nivel_granularidad": generic}),
        FactEgresados(**_tracked_row(2025, 5.0)),
    ])
    session.commit()
    recompute_graduate_trends(session)
    session.commit()
    try:
        client = _client(session)
        listed = client.get("/api/v1/graduates/institutions/list", params={"country": "CHL"}).json()
        assert listed == [{"pais": "chile", "institucion": "CFT ALFA", "n_carreras": 1},
                          {"pais": "chile", "institucion": "Universidad Diego Portales", "n_carreras": 2}]
        assert client.get("/api/v1/graduates/institutions/list", params={"country": "ARG"}).json() == []
        out = client.get("/api/v1/graduates/institutions/careers",
                         params={"institucion": "Universidad Diego Portales"}).json()
        careers = {c["nombre"]: c for c in out["carreras"]}
        assert careers["Enfermería"]["por_anio"] == {"2024": 3.0, "2025": 8.0}
        assert careers["Enfermería"]["es_seguimiento"] is False
        program = careers["DIPLOMADO EN INTELIGENCIA ARTIFICIAL"]
        assert program["es_seguimiento"] and program["tema"] == "Inteligencia artificial"
        assert client.get("/api/v1/graduates/institutions/careers",
                          params={"institucion": "No existe"}).json()["carreras"] == []
    finally:
        app.dependency_overrides.clear()


def test_a_program_named_like_a_generic_career_does_not_double_its_institutions(session):
    session.add(FactEgresados(**_tracked_row(2025, 9.0, "Pregrado", "INGENIERIA EN MINAS")))
    session.add(FactEgresados(**{**_tracked_row(2025, 8.0, "Pregrado", "Ingeniería en Minas"),
                                 "nivel_granularidad": TRACKED["institution_granularity"]}))
    session.commit()
    assert career_institutions(session, "chile", "Ingeniería en Minas")["totales"] == {2025: 8.0}


def test_totals_per_country_do_not_count_programs_twice_unless_a_topic_is_chosen(session):
    session.add(_graduate(2025, 50.0))
    session.add(FactEgresados(**_tracked_row(2025, 9.0)))
    session.commit()
    try:
        client = _client(session)
        everything = client.get("/api/v1/graduates/totals").json()
        assert everything == {"anios": [2025], "paises": [{"pais": "chile", "por_anio": {"2025": 50.0}}]}
        topic = client.get("/api/v1/graduates/totals", params={"tema": "Inteligencia artificial"}).json()
        assert topic["paises"][0]["por_anio"] == {"2025": 9.0}
        health = client.get("/api/v1/graduates/totals", params={"sector": "health"}).json()
        assert health["paises"][0]["por_anio"] == {"2025": 50.0}
        assert client.get("/api/v1/graduates/totals", params={"sector": "energy"}).json()["paises"] == []
    finally:
        app.dependency_overrides.clear()


def test_institution_sums_that_do_not_match_load_nothing(session, monkeypatch, tmp_path):
    session.add(Source(source_id=2, source_code="carreras_seguimiento", name="C", source_kind="dataset"))
    session.commit()
    module = _offline_tracked(monkeypatch, tmp_path)
    bad = {"control": "URY X", "anio": 2024, "valor": 1, "esperado": 2, "ok": False}
    monkeypatch.setattr(module, "read_all", lambda *a: ([_tracked_row(2025, 5.0)], [bad], []))
    with pytest.raises(DatasetError):
        run_tracked_careers_source(session, "carreras_seguimiento", _run(session))
    session.commit()
    assert session.scalars(select(FactEgresados)).first() is None
    assert session.scalars(select(DatasetFile)).one().status == "format_changed"


def _mec_book(path, totals=(5, 4)):
    book = openpyxl.Workbook()
    public = book.active
    public.title = "II-7.2.1"
    rows = [("TOTAL UNIVERSIDADES PÚBLICAS", 10, True), ("TOTAL UDELAR", totals[0], True),
            ("FACULTAD DE DERECHO", 5, True), ("Doctor en Derecho y Ciencias Sociales", 3, False),
            ("Abogacía", 2, False), ("Fuente: MEC", None, False)]
    for i, (name, value, bold) in enumerate(rows, 1):
        public.cell(i, 1, name).font = Font(bold=bold)
        public.cell(i, 8, value)
    private = book.create_sheet("II-7.2.2")
    for i, (name, value, bold) in enumerate([("TOTAL", 4, True), ("UCU", totals[1], True),
                                             ("Abogacía", 4, False)], 1):
        private.cell(i, 1, name).font = Font(bold=bold)
        private.cell(i, 8, value)
    institutes = book.create_sheet("II-7.2.3")
    institutes.cell(1, 1, "TOTAL").font = Font(bold=True)
    institutes.cell(1, 8, 0)
    book.save(path)
    return path


def test_uruguay_yearbook_gives_each_career_its_institution(tmp_path):
    rows, controls = read_uruguay_yearbook(_mec_book(tmp_path / "mec.xlsx"), 2024, TRACKED)
    found = {(r["carrera_objetivo"], r["institucion"]): r["valor"] for r in rows}
    assert found == {("Abogacía", "Universidad de la República (Udelar)"): 5.0,
                     ("Abogacía", "Universidad Católica del Uruguay (UCU)"): 4.0}
    assert {r["pais"] for r in rows} == {"URY"} and all(c["ok"] for c in controls)


def test_uruguay_sum_that_misses_the_published_total_fails_its_control(tmp_path):
    _, controls = read_uruguay_yearbook(_mec_book(tmp_path / "mec.xlsx", totals=(50, 4)), 2024, TRACKED)
    assert [c["ok"] for c in controls if "Udelar" in c["control"]] == [False]


def _diu_zip(path, total=7):
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = "C 2.1.14"
    ws.append([None, "Cuadro 2.1.14 - Estudiantes, nuevos inscriptos, reinscriptos y egresados de títulos de "
                     "pregrado y grado por disciplina según institución. Año 2024"])
    ws.append([])
    ws.append([None, "Total general", "Medicina", None, None, None, "Informática"])
    ws.append([None, None, "EST", "NI", "RE", "EGRE", "EST", "NI", "RE", "EGRE"])
    ws.append([None, None, 99, 9, 90, total - 2, 9, 1, 8, 2])
    ws.append([None, "Total Universidades Nacionales", 99, 9, 90, total - 2, 9, 1, 8, 2])
    ws.append([None, "Buenos Aires", 90, 8, 82, 3, 9, 1, 8, 2])
    ws.append([None, "Rosario (2)", 9, 1, 8, 2, "-", "-", "-", "-"])
    ws.append([None, "Total Institutos Universitarios Nacionales", 0, 0, 0, 0, 0, 0, 0, 0])
    ws.append([None, "(2) Una nota"])
    buffer = io.BytesIO()
    book.save(buffer)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Z 2.1 Pregrado y Grado Gestión Estatal 24.xlsx", buffer.getvalue())
    return path


def _read_diu(path, release=None):
    return read_argentina_yearbook(path, TRACKED, "Pregrado y Grado", "Pregrado y grado", "anuario_diu_argentina", release)


def test_argentine_yearbook_reads_graduates_per_discipline_and_institution(tmp_path):
    rows, controls, unknown = _read_diu(_diu_zip(tmp_path / "diu.zip"))
    assert unknown == set()
    found = {(r["carrera_objetivo"], r["institucion"]): r["valor"] for r in rows}
    assert found == {("Medicina", "Universidad de Buenos Aires"): 3.0,
                     ("Informática", "Universidad de Buenos Aires"): 2.0,
                     ("Medicina", "Universidad Nacional de Rosario"): 2.0}
    assert {(r["pais"], r["anio"], r["nivel"]) for r in rows} == {("ARG", 2024, "Pregrado y grado")}
    assert [c["ok"] for c in controls] == [True]


def test_argentine_sum_that_misses_the_table_total_fails_its_control(tmp_path):
    _, controls, _ = _read_diu(_diu_zip(tmp_path / "diu.zip", total=70))
    assert [c["ok"] for c in controls] == [False]


def test_yearbook_of_another_year_is_refused(tmp_path):
    with pytest.raises(ValueError):
        _read_diu(_diu_zip(tmp_path / "diu.zip"), release=2023)


def _diu_variant(path, disciplines=("Medicina", "Filosafía", "Nueva Disciplina"), subtotal="Universidades Privadas"):
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = "cuadro_2_2_10"
    ws.append(["Cuadro 2.2.10 - Estudiantes, nuevas/os inscriptas/os, reinscriptas/os y egresadas/os de títulos de"])
    ws.append(["pregrado y grado por disciplina según institución, Año 2018"])
    head, kinds, total, group, row = [None, "Total"], [None, "EGR"], ["Total de las Instituciones", 9], [subtotal, 9], ["Buenos Aires", 9]
    for name in disciplines:
        head += [name, None]
        kinds += ["EST", "EGR"]
        total += [50, 3]
        group += [50, 3]
        row += [50, 3]
    for line in (head, kinds, total, group, row):
        ws.append(line)
    buffer = io.BytesIO()
    book.save(buffer)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("2.2 Pregrado y Grado.xlsx", buffer.getvalue())
    return path


def test_yearbook_variants_titles_typos_unlabeled_subtotals_and_unknown_columns(tmp_path):
    rows, controls, unknown = _read_diu(_diu_variant(tmp_path / "v.zip"), release=2018)
    found = {(r["carrera_objetivo"], r["institucion"]): r["valor"] for r in rows}
    assert found == {("Medicina", "Universidad de Buenos Aires"): 3.0, ("Filosofía", "Universidad de Buenos Aires"): 3.0}
    assert unknown == {"Nueva Disciplina"}
    assert controls[0]["valor"] == 6.0 and controls[0]["esperado"] == 9.0  # measured against its own total column


def test_every_csv_discipline_column_is_a_known_career():
    table = yaml.safe_load((settings.config_dir / TRACKED["argentina"]["names_file"]).read_bytes())
    known = set(argentine_disciplines(TRACKED).values())
    assert set(table["columnas_csv"].values()) <= known


def test_year_filter_gives_observed_then_projected_values(session):
    session.add_all([_graduate(y, 100.0 + y - 2007) for y in range(2007, 2026)])
    session.add_all([FactEgresados(**_tracked_row(y, 10.0)) for y in (2024, 2025)])
    session.commit()
    recompute_graduate_trends(session)
    session.commit()

    def override():
        yield session

    app.dependency_overrides[get_session] = override
    try:
        client = TestClient(app)
        years = client.get("/api/v1/graduates/by-year").json()
        assert years["anio"] is None and years["items"] == []
        assert years["anios_observados"][-1] == 2025 and years["anios_proyectados"][0] == 2026
        observed = client.get("/api/v1/graduates/by-year", params={"year": 2025, "country": "CHL"}).json()
        assert {i["nombre"]: i["tipo"] for i in observed["items"]} == {
            "Enfermería": "observado", "DIPLOMADO EN INTELIGENCIA ARTIFICIAL": "observado"}
        assert [i["es_seguimiento"] for i in observed["items"]] == [False, True]
        future = client.get("/api/v1/graduates/by-year", params={"year": 2027}).json()
        item = next(i for i in future["items"] if i["nombre"] == "Enfermería")
        assert item["tipo"] == "proyectado" and item["limite_inferior"] <= item["graduados"]
        assert client.get("/api/v1/graduates/by-year", params={"year": 1990}).json()["items"] == []
    finally:
        app.dependency_overrides.clear()
