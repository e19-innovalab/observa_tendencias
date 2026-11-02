from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_session
from app.main import app
from app.models import (
    Base,
    CoverageReport,
    FactSalario,
    GraduateProjection,
    GraduateTrend,
    JobPosting,
    ReporteDensidadProfesional,
)


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(
        engine,
        tables=[t.__table__ for t in (
            CoverageReport,
            JobPosting,
            GraduateTrend,
            GraduateProjection,
            ReporteDensidadProfesional,
            FactSalario,
        )],
    )
    with Session(engine) as s:
        for nombre, tend, var in [("medicina", "growing", 25.0), ("enfermeria", "declining", -11.1)]:
            s.add(GraduateTrend(pais="chile", nombre=nombre, anio_desde=2007, anio_hasta=2025,
                                n_anios_serie=19, ventana_anios=5, graduados_inicio_ventana=100,
                                graduados_ultimo=125, variacion_ventana_pct=var, tendencia=tend,
                                tiene_huecos=False, proyeccion="generada"))
        s.add(GraduateProjection(pais="chile", nombre="medicina", anio=2026,
                                 graduados_proyectado=130, limite_inferior=90, limite_superior=170))
        s.add(CoverageReport(pais="CHL", sector="Salud", n_anios_observados=19, anio_min=2007,
                             anio_max=2025, elegible_proyeccion=True, estado="proyectable"))
        for i, (prov, sec) in enumerate([("Santa Fe", "Salud"), ("Santa Fe", "Otros"),
                                         ("Córdoba", "Salud")]):
            s.add(JobPosting(id=str(i), pais="ARG", provincia=prov, sector=sec,
                             regla_clasificacion="industria", titulo=f"Oferta {i}",
                             fecha_publicacion=date(2026, 10, 8), url="https://x/" + str(i),
                             scraped_at=datetime(2026, 10, 13, 17, 0, tzinfo=UTC)))

        # Datos para pruebas de densidad profesional (ARG 2022, CHL 2022 y 2025)
        s.add_all([
            ReporteDensidadProfesional(
                pais="ARG", sector="Tecnología", anio=2022, graduados_anuales=2813.0,
                puestos_empleo=271486.0, graduados_por_mil_ocupados=10.36,
                ratio_graduados_vs_empleo_pct=1.036, fuente_graduados="Araucano_SPU",
                fuente_empleo="OIT_ILOSTAT", concepto="Graduados anuales por cada 1.000 ocupados",
            ),
            ReporteDensidadProfesional(
                pais="CHL", sector="Tecnología", anio=2022, graduados_anuales=9505.0,
                puestos_empleo=202404.0, graduados_por_mil_ocupados=46.96,
                ratio_graduados_vs_empleo_pct=4.696, fuente_graduados="SIES_MiFuturo",
                fuente_empleo="OIT_ILOSTAT", concepto="Graduados anuales por cada 1.000 ocupados",
            ),
            ReporteDensidadProfesional(
                pais="CHL", sector="Tecnología", anio=2025, graduados_anuales=11230.0,
                puestos_empleo=225000.0, graduados_por_mil_ocupados=49.91,
                ratio_graduados_vs_empleo_pct=4.991, fuente_graduados="SIES_MiFuturo",
                fuente_empleo="OIT_ILOSTAT", concepto="Graduados anuales por cada 1.000 ocupados",
            ),
        ])

        # Datos para pruebas de salarios duales
        s.add_all([
            FactSalario(
                pais="ARG", sector="Tecnología", anio=2024, fuente_id="OIT_ILOSTAT",
                sexo="TOTAL", salario_usd_ppa=1850.0, tipo_salario="promedio_mensual_usd_ppa",
                metodo_ppa="PA.NUS.PPP", es_observado=True,
            ),
            FactSalario(
                pais="ARG", sector="Tecnología", anio=2023, fuente_id="AR_CEPXXI",
                sexo="TOTAL", carrera_objetivo="Ingeniería en Sistemas", salario_moneda_local=850000.0,
                moneda_local="ARS", salario_usd_ppa=1720.0, es_observado=True,
            ),
        ])
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_jobs_filters(client):
    r = client.get("/api/v1/jobs", params={"provincia": "Santa Fe", "sector": "Salud"}).json()
    assert r["total"] == 1 and r["items"][0]["id"] == "0"


def test_jobs_summary(client):
    r = client.get("/api/v1/jobs/summary", params={"pais": "arg"}).json()
    assert r["total"] == 3
    assert {"provincia": "Santa Fe", "sector": "Otros", "n": 1} in r["por_provincia_sector"]
    # how to show it comes from app.yaml (jobs_view), the same for every client
    from app.core.config_files import app_config

    view = app_config().jobs_view
    assert r["view"]["notice"] == view.notice and r["view"]["page_size"] == view.page_size
    assert r["view"]["other_sector"] not in r["view"]["sector_order"]


def test_coverage(client):
    r = client.get("/api/v1/coverage", params={"pais": "chl"}).json()
    assert r[0]["estado"] == "proyectable"


def test_graduate_trends_filter(client):
    r = client.get("/api/v1/graduates/trends", params={"pais": "CHILE", "tendencia": "declining"}).json()
    assert [i["nombre"] for i in r["items"]] == ["enfermeria"]
    assert "orientativas" in r["source"]


def test_graduate_projections(client):
    r = client.get("/api/v1/graduates/projections", params={"nombre": "medicina"}).json()
    assert r[0]["anio"] == 2026 and r[0]["limite_inferior"] <= r[0]["graduados_proyectado"]


def test_country_and_legacy_pais_are_equivalent(client):
    for path in ("/api/v1/jobs/summary", "/api/v1/coverage"):
        a = client.get(path, params={"pais": "chl" if "coverage" in path else "arg"}).json()
        b = client.get(path, params={"country": "CHL" if "coverage" in path else "ARG"}).json()
        assert a == b
    trends = client.get("/api/v1/graduates/trends", params={"country": "CHL"}).json()
    assert {i["pais"] for i in trends["items"]} == {"chile"}
    proj = client.get("/api/v1/graduates/projections", params={"country": "CHL"}).json()
    assert proj and all(p["pais"] == "chile" for p in proj)


def test_jobs_competition_median_and_cap(monkeypatch):
    """Median applicants per posting; LinkedIn's "200+" is counted apart; small sectors get none."""
    from app.api.v1.jobs import _competition
    from app.core.config_files import app_config

    view = app_config().jobs_view
    monkeypatch.setattr(view, "competition_min_postings", 3)
    c = _competition("Energía", [10, 50, view.applicants_cap, view.applicants_cap, None])
    assert (c.ofertas, c.con_postulantes) == (5, 4)
    assert c.mediana_postulantes == (50 + view.applicants_cap) / 2
    assert c.en_tope == 0.5
    small = _competition("Salud", [10, 20])
    assert small.mediana_postulantes is None and small.en_tope is None


def test_analytics_densidad_profesional_enfoques(client):
    # Enfoque regional comun: solo anios de la ventana armonizada (2022 presente, 2025 excluido)
    r_reg = client.get("/api/v1/analytics/densidad-profesional", params={"enfoque": "regional_comun"}).json()
    assert r_reg["enfoque"] == "regional_comun"
    anios_reg = {item["anio"] for item in r_reg["items"]}
    assert 2022 in anios_reg and 2025 not in anios_reg
    assert r_reg["total"] == 2  # ARG 2022 y CHL 2022

    # Enfoque local para Chile: incluye 2025 (su corte mas reciente)
    r_loc = client.get("/api/v1/analytics/densidad-profesional", params={"enfoque": "local", "country": "CHL"}).json()
    assert r_loc["enfoque"] == "local"
    assert r_loc["total"] == 2
    assert any(i["anio"] == 2025 for i in r_loc["items"])


def test_analytics_salarios_dual(client):
    # Enfoque regional OIT
    r_reg = client.get("/api/v1/analytics/salarios/dual", params={"enfoque": "regional"}).json()
    assert r_reg["enfoque"] == "regional"
    assert r_reg["total"] == 1
    assert r_reg["items"][0]["fuente_id"] == "OIT_ILOSTAT"
    assert r_reg["items"][0]["salario_usd_ppa"] == 1850.0

    # Enfoque local CEP-XXI
    r_loc = client.get("/api/v1/analytics/salarios/dual", params={"enfoque": "local"}).json()
    assert r_loc["enfoque"] == "local"
    assert r_loc["total"] == 1
    assert r_loc["items"][0]["fuente_id"] == "AR_CEPXXI"
    assert r_loc["items"][0]["salario_moneda_local"] == 850000.0


def test_analytics_ise_metodologia_insercion(client):
    r = client.get("/api/v1/analytics/ise/metodologia-insercion").json()
    assert r["version"] == "0.2"
    assert r["pesos_efectivos_redistribuidos"]["insertion_rate"] == 0.0
    assert r["pesos_efectivos_redistribuidos"]["net_demand"] == 0.467
    assert "CHL" in r["disponibilidad_por_pais"]


def test_analytics_habilidades_general(client):
    for endpoint in ["/api/v1/analytics/habilidades", "/api/v1/analytics/habilidades-ia"]:
        r = client.get(endpoint).json()
        assert r["total"] == 114
        assert "Tecnología" in r["resumen_por_sector"]
        assert "Salud" in r["resumen_por_sector"]
        assert "Energía" in r["resumen_por_sector"]
        assert "Economía del conocimiento" in r["resumen_por_sector"]
        assert "Turismo" in r["resumen_por_sector"]
        assert len(r["items"]) == 114

        # Verificar estructura integral del primer item
        first = r["items"][0]
        assert "carrera_id" in first
        assert "ciuo_08" in first
        assert "habilidades_nucleares" in first
        assert "habilidades_emergentes_sector" in first
        assert "habilidades_transversales_humanas" in first
        assert "habilidades_digitales_ia" in first
        assert "vector_emergencia" in first
        assert "oit_gradiente" in first
        assert "demanda_observada_linkedin" in first
        assert "recomendacion_curricular" in first


def test_analytics_habilidades_filtros(client):
    # Filtro por sector Tecnología
    r_tech = client.get("/api/v1/analytics/habilidades", params={"sector": "Tecnología"}).json()
    assert r_tech["sector_filtro"] == "Tecnología"
    assert r_tech["total"] == 55
    assert all(it["sector"] == "Tecnología" for it in r_tech["items"])

    # Filtro por vector de emergencia sectorial (ej. Transición Energética)
    r_trans = client.get("/api/v1/analytics/habilidades", params={"vector": "Transición"}).json()
    assert r_trans["total"] >= 1
    assert any("Transición" in (it.get("vector_emergencia") or "") for it in r_trans["items"])

    # Filtro por CIUO 2512 (Desarrolladores de software)
    r_ciuo = client.get("/api/v1/analytics/habilidades", params={"ciuo": "2512"}).json()
    assert r_ciuo["total"] >= 1
    dev = next(it for it in r_ciuo["items"] if it["ciuo_08"] == "2512")
    assert "Algoritmos" in dev["habilidades_nucleares"]
    assert "Microservicios" in dev["habilidades_emergentes_sector"] or "microservicios" in dev["habilidades_emergentes_sector"]
    assert "Scrum" in dev["habilidades_transversales_humanas"]
    assert dev["oit_gradiente"] == "Gradient 3"
