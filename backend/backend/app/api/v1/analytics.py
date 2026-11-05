"""Endpoints analíticos dimensionales (Plan de Integración - Etapas 3 y 4).

Proporciona acceso a la Tasa de Densidad Profesional por sector, series salariales
duales (local vs regional PPA) y la matriz de habilidades ocupacionales vs impacto IA (OIT WP 140 / LinkedIn).
"""
import csv
from collections import Counter
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.sector_kpis_run import sector_kpis
from app.core.database import get_session
from app.models import FactSalario, ReporteDensidadProfesional
from app.schemas.analytics import (
    DensidadProfesionalItem,
    DensidadProfesionalResponse,
    MatrizHabilidadIAItem,
    MatrizHabilidadIAResponse,
    SalarioDualItem,
    SalarioDualResponse,
    SectorKpis,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


ANIO_COMUN_REGIONAL = 2022
ANIOS_COMUNES_TRIPARTITOS = [2018, 2020, 2021, 2022]
ULTIMO_ANIO_OBSERVADO = {"ARG": 2022, "CHL": 2025, "URY": 2023}


@router.get("/sectores", response_model=SectorKpis)
def sectores(session: Session = Depends(get_session)):
    """KPIs por país, sector y año: densidad profesional, empleo, participación de las mujeres y
    salarios por sexo, más la proyección de titulados por sector."""
    return SectorKpis(**sector_kpis(session))


@router.get("/densidad-profesional", response_model=DensidadProfesionalResponse)
def densidad_profesional(
    country: str | None = Query(None, description="ISO3 (ARG, CHL, URY)"),
    pais: str | None = Query(None, description="Igual que country"),
    sector: str | None = Query(None, description="Sector estratégico"),
    year: int | None = Query(None, description="Año específico"),
    anio: int | None = Query(None, description="Igual que year"),
    enfoque: Literal["local", "regional_comun", "todos"] = Query(
        "todos",
        description="local: serie histórica por país | regional_comun: ventana común tripartita | todos",
    ),
    session: Session = Depends(get_session),
):
    """Tasa de Densidad Profesional (Graduados por cada 1.000 ocupados del sector) con Enfoque Dual."""
    c = (country or pais).upper() if (country or pais) else None
    a = year or anio

    stmt = select(ReporteDensidadProfesional)

    if c:
        stmt = stmt.where(ReporteDensidadProfesional.pais == c)
    if sector:
        stmt = stmt.where(ReporteDensidadProfesional.sector.ilike(f"%{sector}%"))

    if enfoque == "regional_comun":
        if a:
            stmt = stmt.where(ReporteDensidadProfesional.anio == a)
        else:
            stmt = stmt.where(ReporteDensidadProfesional.anio.in_(ANIOS_COMUNES_TRIPARTITOS))
        stmt = stmt.order_by(
            ReporteDensidadProfesional.anio.desc(),
            ReporteDensidadProfesional.sector,
            ReporteDensidadProfesional.pais,
        )
        nota = (
            "Ventana común armonizada tripartita (2018-2022) para cotejo comparativo regional "
            "sin distorsiones temporales (Año común de referencia: 2022)."
        )
        ventana = f"Ventana común 2018-2022 (Año común: {ANIO_COMUN_REGIONAL})"

    elif enfoque == "local":
        if a:
            stmt = stmt.where(ReporteDensidadProfesional.anio == a)
        stmt = stmt.order_by(
            ReporteDensidadProfesional.pais,
            ReporteDensidadProfesional.sector,
            ReporteDensidadProfesional.anio.desc(),
        )
        nota = (
            "Enfoque local con máxima actualidad observada por país para diagnóstico interno y planificación educativa "
            "(el último año disponible varía por país)."
        )
        ventana = "Serie histórica observada por país"

    else:
        if a:
            stmt = stmt.where(ReporteDensidadProfesional.anio == a)
        stmt = stmt.order_by(
            ReporteDensidadProfesional.pais,
            ReporteDensidadProfesional.sector,
            ReporteDensidadProfesional.anio,
        )
        nota = "Conjunto completo de observaciones de densidad profesional (graduados anuales vs puestos de trabajo)."
        ventana = "Todas las observaciones (2013-2025)"

    rows = session.scalars(stmt).all()
    items = [DensidadProfesionalItem.model_validate(r) for r in rows]

    return DensidadProfesionalResponse(
        total=len(items),
        enfoque=enfoque,
        ventana_temporal=ventana,
        nota_metodologica=nota,
        items=items,
    )


@router.get("/salarios/dual", response_model=SalarioDualResponse)
def salarios_dual(
    country: str | None = Query(None, description="ISO3 (ARG, CHL, URY)"),
    pais: str | None = Query(None, description="Igual que country"),
    sector: str | None = Query(None, description="Sector estratégico"),
    year: int | None = Query(None, description="Año específico"),
    anio: int | None = Query(None, description="Igual que year"),
    enfoque: Literal["local", "regional", "todos"] = Query(
        "todos",
        description="local: series salariales locales deflactadas | regional: OIT 2024 en USD PPA | todos",
    ),
    session: Session = Depends(get_session),
):
    """Series salariales con Enfoque Dual: evolución interna local deflactada vs comparativa OIT 2024 USD PPA."""
    c = (country or pais).upper() if (country or pais) else None
    a = year or anio

    stmt = select(FactSalario)

    if c:
        stmt = stmt.where(FactSalario.pais == c)
    if sector:
        stmt = stmt.where(FactSalario.sector.ilike(f"%{sector}%"))
    if a:
        stmt = stmt.where(FactSalario.anio == a)

    if enfoque == "regional":
        stmt = stmt.where(
            FactSalario.fuente_id.ilike("%OIT%"),
            FactSalario.salario_usd_ppa.isnot(None),
        ).order_by(FactSalario.sector, FactSalario.pais)
        nota = (
            "Comparativa regional con la serie de la OIT en dólares a paridad de poder adquisitivo "
            "(CUR_TYPE_PPP)."
        )
    elif enfoque == "local":
        stmt = stmt.where(
            ~FactSalario.fuente_id.ilike("%OIT%"),
        ).order_by(FactSalario.pais, FactSalario.sector, FactSalario.anio.desc())
        nota = (
            "Salarios del sector privado registrado de Argentina (CEP-XXI), hasta noviembre de 2023. "
            "Los de Chile (Buscador del SIES) no se cargan: no tienen descarga pública."
        )
    else:
        stmt = stmt.order_by(FactSalario.pais, FactSalario.sector, FactSalario.anio.desc())
        nota = "Base consolidada de hechos salariales (series locales oficiales y matriz regional supranacional)."

    rows = session.scalars(stmt).all()
    items = [SalarioDualItem.model_validate(r) for r in rows]

    return SalarioDualResponse(
        total=len(items),
        enfoque=enfoque,
        nota_metodologica=nota,
        items=items,
    )


_MATRIZ_IA_CACHE: list[dict] | None = None


def _load_matriz_habilidades_ia() -> list[dict]:
    global _MATRIZ_IA_CACHE
    if _MATRIZ_IA_CACHE is not None:
        return _MATRIZ_IA_CACHE

    cur = Path(__file__).resolve()
    candidatos = [
        cur.parents[4] / "data" / "processed" / "data_analytics" / "matriz_habilidades_riesgo_ia_sector.csv",
        cur.parents[5] / "data_analytics" / "output" / "matriz_habilidades_riesgo_ia_sector.csv",
        cur.parents[5] / "data_analytics" / "data" / "processed" / "matriz_habilidades_riesgo_ia_sector.csv",
    ]
    path_encontrado = None
    for c in candidatos:
        if c.exists():
            path_encontrado = c
            break

    if not path_encontrado:
        _MATRIZ_IA_CACHE = []
        return _MATRIZ_IA_CACHE

    items = []
    with open(path_encontrado, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append({
                "carrera_id": row["carrera_id"],
                "carrera_objetivo": row["carrera_objetivo"],
                "sector": row["sector"],
                "cine_f_codigo": row["cine_f_codigo"],
                "nivel_esperado": row["nivel_esperado"],
                "ciuo_08": row["ciuo_08"],
                "ocupacion_nombre_es": row["ocupacion_nombre_es"],
                "ocupacion_nombre_en": row["ocupacion_nombre_en"],
                "oit_exposicion_media": float(row["oit_exposicion_media"]),
                "oit_desvio_std": float(row["oit_desvio_std"]),
                "oit_gradiente": row["oit_gradiente"],
                "tipologia_habilidad": row["tipologia_habilidad"],
                "vector_emergencia": row.get("vector_emergencia"),
                "habilidades_nucleares": row.get("habilidades_nucleares"),
                "habilidades_emergentes_sector": row.get("habilidades_emergentes_sector"),
                "habilidades_transversales_humanas": row.get("habilidades_transversales_humanas"),
                "habilidades_digitales_ia": row.get("habilidades_digitales_ia"),
                "impacto_ia_resumen": row["impacto_ia_resumen"],
                "habilidades_clave_esco": row["habilidades_clave_esco"],
                "demanda_observada_linkedin": row["demanda_observada_linkedin"],
                "recomendacion_curricular": row["recomendacion_curricular"],
                "fuente_mapeo": row["fuente_mapeo"],
                "fuente_ofertas": row["fuente_ofertas"],
            })
    _MATRIZ_IA_CACHE = items
    return _MATRIZ_IA_CACHE


@router.get("/habilidades", response_model=MatrizHabilidadIAResponse)
@router.get("/habilidades-ia", response_model=MatrizHabilidadIAResponse)
def matriz_habilidades_sectoriales(
    sector: str | None = Query(None, description="Filtrar por sector estratégico (ej. 'Tecnología', 'Salud')"),
    tipologia: str | None = Query(None, description="Filtrar por tipología (ej. 'Nuclear', 'Emergente', 'Transformación')"),
    vector: str | None = Query(None, description="Filtrar por vector de demanda (ej. 'Transición', 'Sostenibilidad', 'Cloud')"),
    ciuo: str | None = Query(None, description="Código CIUO-08 de 4 dígitos (ej. '2512')"),
    gradiente: str | None = Query(None, description="Gradiente OIT (ej. 'Gradient 3', 'Not Exposed')"),
):
    """Matriz metodológica integral de habilidades sectoriales (Nucleares, Emergentes, Transversales, Digitales/IA)."""
    all_items = _load_matriz_habilidades_ia()

    filtered = all_items
    if sector:
        filtered = [it for it in filtered if sector.lower() in it["sector"].lower()]
    if tipologia:
        filtered = [it for it in filtered if tipologia.lower() in it["tipologia_habilidad"].lower()]
    if vector:
        filtered = [it for it in filtered if it.get("vector_emergencia") and vector.lower() in it["vector_emergencia"].lower()]
    if ciuo:
        filtered = [it for it in filtered if it["ciuo_08"] == str(ciuo).zfill(4)]
    if gradiente:
        filtered = [it for it in filtered if gradiente.lower() in it["oit_gradiente"].lower()]

    sec_summary = Counter(it["sector"] for it in all_items)
    tip_summary = Counter(it["tipologia_habilidad"] for it in all_items)

    nota = (
        "Articulación metodológica integral de competencias sectoriales (Hard Skills nucleares, Habilidades Emergentes, "
        "Transversales Humanas y Digitales/IA) para las 25 carreras objetivo en los 5 sectores estratégicos del Cono Sur "
        "(ARG, CHL, URY), con métricas de exposición a IA OIT (WP 140) y validación en ofertas de empleo de LinkedIn."
    )

    return MatrizHabilidadIAResponse(
        total=len(filtered),
        sector_filtro=sector,
        tipologia_filtro=tipologia,
        resumen_por_sector=dict(sec_summary),
        resumen_por_tipologia=dict(tip_summary),
        nota_metodologica=nota,
        items=[MatrizHabilidadIAItem.model_validate(it) for it in filtered],
    )


