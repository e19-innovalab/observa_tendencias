import io
import zipfile

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics import sector_kpis_run
from app.analytics.graduate_trends_run import CareerSeries
from app.analytics.sector_kpis_run import (
    density_rows,
    earnings_rows,
    employment_rows,
    gender_rows,
    graduates_by_sector,
    projection_rows,
    recompute_sector_tables,
)
from app.core.config_files import analytics_params
from app.core.database import get_session
from app.datasets.tracked_careers import read_argentina_sex_totals
from app.main import app
from app.models import (
    AnalisisGeneroIntegral,
    Base,
    Country,
    DatasetFile,
    FactEgresados,
    FactOcupacionTerciarios,
    FactoresMacroPPA,
    FactSalario,
    Graduate,
    GraduateProjection,
    GraduateTrend,
    IngestionRun,
    ProyeccionesGraduadosSector,
    ReporteDensidadProfesional,
    Source,
    TipoCambioDiario,
)

TRACKED = analytics_params("tracked_careers")


def _series(pais, sector, by_year, tracked=False):
    return CareerSeries(pais, "x", by_year, max(by_year), tracked=tracked, sector=sector)


def test_graduates_add_up_by_sector_and_country_without_programs_found_by_topic():
    totals = graduates_by_sector([
        _series("chile", "health", {2024: 10.0}), _series("chile", "health", {2024: 5.0}),
        _series("chile", None, {2024: 7.0}), _series("chile", "technology", {2024: 99.0}, tracked=True),
    ])
    assert totals == {("CHL", None, 2024): 22.0, ("CHL", "health", 2024): 15.0}


def test_density_is_graduates_per_thousand_employed_and_needs_both_sides():
    rows = density_rows({("CHL", "health", 2024): 500.0, ("CHL", "energy", 2024): 9.0},
                        {("CHL", "health", 2024): 250.0})
    assert len(rows) == 1
    assert rows[0]["sector"] == "Salud" and rows[0]["graduados_por_mil_ocupados"] == 2.0
    assert rows[0]["puestos_empleo"] == 250000.0 and rows[0]["ratio_graduados_vs_empleo_pct"] == 0.2


def test_employment_share_of_women_is_empty_without_the_series():
    rows = employment_rows({("ARG", None, 2024): 100.0, ("URY", None, 2024): 50.0}, {("ARG", None, 2024): 40.0})
    shares = {r["pais"]: r["share_mujeres"] for r in rows}
    assert shares == {"ARG": 40.0, "URY": None} and rows[0]["sector"] == "Total"


def test_earnings_keep_one_row_per_sex():
    rows = earnings_rows({("URY", "health", 2024): 10.0}, {("URY", "health", 2024): 9.0}, {("URY", "health", 2024): 11.0})
    assert {r["sexo"]: r["salario_usd_ppa"] for r in rows} == {"T": 10.0, "F": 9.0, "M": 11.0}


def test_gender_compares_graduates_and_employment_and_labels_parity():
    rows = gender_rows({("CHL", "health", 2024): {"F": 70.0, "M": 29.0, "NB": 1.0},
                        ("CHL", "technology", 2024): {"F": 50.0, "M": 50.0}},
                       {("CHL", "health", 2024): 200.0}, {("CHL", "health", 2024): 150.0})
    health = next(r for r in rows if r["sector"] == "Salud")
    assert health["pct_mujeres_graduadas"] == 70.0 and health["pct_mujeres_empleadas"] == 75.0
    assert health["brecha_graduados_pct"] == 41.0 and health["diagnostico_paridad"] == "Concentración femenina"
    tech = next(r for r in rows if r["sector"] == "Tecnología")
    assert tech["diagnostico_paridad"] == "Zona de paridad" and tech["pct_mujeres_empleadas"] is None
    # the band is 40 % to 60 %, and a handful of people gets no diagnosis
    few = gender_rows({("URY", "tourism", 2024): {"F": 8.0, "M": 2.0}}, {}, {})[0]
    assert few["diagnostico_paridad"] == "Pocos casos"
    men = gender_rows({("CHL", "energy", 2024): {"F": 39.0, "M": 61.0}}, {}, {})[0]
    assert men["diagnostico_paridad"] == "Subrepresentación femenina"
    edge = gender_rows({("CHL", "energy", 2024): {"F": 40.0, "M": 60.0}}, {}, {})[0]
    assert edge["diagnostico_paridad"] == "Zona de paridad"


def test_projection_needs_history_without_gaps_and_only_covers_sectors():
    long = {("CHL", "health", 2007 + i): 100.0 + i * 5 for i in range(15)}
    gaps = {("CHL", "energy", y): 50.0 for y in range(2007, 2022) if y != 2015}
    short = {("URY", "health", y): 9.0 for y in range(2020, 2025)}
    total = {("CHL", None, y): 9.0 for y in range(2007, 2022)}
    rows = projection_rows({**long, **gaps, **short, **total})
    assert {r["sector"] for r in rows} == {"Salud"} and {r["pais"] for r in rows} == {"CHL"}
    assert [r["anio_proyectado"] for r in rows] == [2022, 2023, 2024, 2025]
    assert all(r["limite_inferior_95"] >= 0 for r in rows)


def _diu_sex(path, title="por género1 según institución. Año 2021", total=(80, 20)):
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = "2.1.4a"
    ws.append([None, f"Cuadro 2.1.4 a - Estudiantes y egresadas/os de títulos de pregrado y grado {title}"])
    ws.append([None, "Institución", "Estudiantes", None, None, "Egresadas/os"])
    ws.append([None, None, "Total", "Mujeres", "Varones", "Total", "Mujeres", "Varones"])
    ws.append([None, "Total de las Instituciones", 500, 300, 200, sum(total), *total])
    ws.append([None, "Buenos Aires", 50, 30, 20, 10, 6, 4])
    percent = book.create_sheet("2.1.4b")
    percent.append([None, "Cuadro 2.1.4 b - egresadas/os de títulos de pregrado y grado por género según institución, en porcentaje. Año 2021"])
    percent.append([None, "Institución", "Egresadas/os"])
    percent.append([None, None, "Total", "Mujeres", "Varones"])
    percent.append([None, "Total", 100, 80.0, 20.0])
    buffer = io.BytesIO()
    book.save(buffer)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("2.1 Pregrado y Grado Estatal.xlsx", buffer.getvalue())
        archive.writestr("2.2 Pregrado y Grado Privada.xlsx", buffer.getvalue())
    return path


def test_argentine_sex_totals_use_the_total_row_of_each_table_and_not_percentages(tmp_path):
    rows, warnings = read_argentina_sex_totals(_diu_sex(tmp_path / "d.zip"), TRACKED, "Pregrado y Grado", "Pregrado y grado", "s", 2021)
    assert {(r["sexo"], r["valor"], r["anio"]) for r in rows} == {("F", 160.0, 2021), ("M", 40.0, 2021)}
    assert {r["pais"] for r in rows} == {"ARG"} and warnings == []


def test_a_yearbook_without_sex_tables_gives_a_warning(tmp_path):
    rows, warnings = read_argentina_sex_totals(_diu_sex(tmp_path / "d.zip", title="por rama"), TRACKED, "Pregrado y Grado", "x", "s", 2021)
    assert rows == [] and "0 cuadros" in warnings[0]


@pytest.fixture
def session():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=[t.__table__ for t in (
        Country, Source, IngestionRun, DatasetFile, Graduate, GraduateTrend, GraduateProjection,
        FactEgresados, ReporteDensidadProfesional, FactOcupacionTerciarios, FactSalario, FactoresMacroPPA, TipoCambioDiario,
        AnalisisGeneroIntegral, ProyeccionesGraduadosSector)])
    with Session(engine) as s:
        s.add(Country(iso3="CHL", name_es="Chile", name_en="Chile"))
        s.add(Source(source_id=1, source_code="mifuturo_chile", name="M", source_kind="dataset"))
        s.add(Source(source_id=2, source_code="ilostat", name="O", source_kind="api"))
        s.commit()
        yield s


def test_tables_fill_and_the_endpoint_joins_them(session, monkeypatch):
    values = {"employment": 250.0, "employment_women": 200.0, "mean_monthly_earnings_ppp": 1000.0,
              "mean_monthly_earnings_ppp_women": 900.0, "mean_monthly_earnings_ppp_men": 1200.0}
    monkeypatch.setattr(sector_kpis_run, "_annual",
                        lambda _session, code: {("CHL", "health", 2024): values[code], ("CHL", None, 2024): values[code]})
    session.add(Graduate(country_iso3="CHL", career_key="enfermeria", career="Enfermería", level="Pregrado",
                         year=2024, graduates=500.0, source_id=1))
    for sex, value in (("F", 400.0), ("M", 100.0)):
        session.add(FactEgresados(pais="CHL", carrera_objetivo="Enfermería", anio=2024, valor=value, sexo=sex,
                                  nivel="Pregrado", fuente_id="mifuturo_chile",
                                  nivel_granularidad=TRACKED["sex_granularity"], es_observado=True))
    session.commit()
    assert recompute_sector_tables(session) > 0
    session.commit()

    def override():
        yield session

    app.dependency_overrides[get_session] = override
    try:
        client = TestClient(app)
        out = client.get("/api/v1/analytics/sectores").json()
        row = next(i for i in out["items"] if i["sector"] == "Salud" and i["anio"] == 2024)
        assert row["densidad"] == 2.0 and row["ocupados"] == 250000.0 and row["pct_mujeres_ocupadas"] == 80.0
        assert row["pct_mujeres_graduadas"] == 80.0 and row["salario_mujeres"] == 900.0
        assert row["brecha_salarial_pct"] == 25.0 and out["nota"]
        total = next(i for i in out["items"] if i["sector"] == "Total")
        assert total["pct_mujeres_graduadas"] == 80.0
        dual = client.get("/api/v1/analytics/densidad-profesional", params={"enfoque": "local", "country": "CHL"}).json()
        assert dual["total"] >= 1
    finally:
        app.dependency_overrides.clear()
    assert session.scalars(select(AnalisisGeneroIntegral)).first().diagnostico_paridad == "Concentración femenina"
