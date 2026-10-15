from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_session
from app.main import app
from app.models import Base, CoverageReport, GraduateProjection, GraduateTrend, JobPosting


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(
        engine,
        tables=[t.__table__ for t in (CoverageReport, JobPosting, GraduateTrend, GraduateProjection)],
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
