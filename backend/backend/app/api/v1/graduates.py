import csv
import io
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.employability_run import Point, dimension_value
from app.analytics.graduate_trends_run import (
    available_years,
    career_institutions,
    career_points,
    institution_careers,
    institution_list,
    totals_by_country,
    values_for_year,
)
from app.analytics.skill_gaps_run import (
    crosswalk_codes,
    crosswalk_levels,
    load_crosswalk,
    supply_growth_conf,
)
from app.core.config_files import analytics_params, app_config, catalog
from app.core.database import get_session
from app.datasets.profiles import normalize_text, profiles
from app.models import (
    FactInstitucionesEgresados,
    Graduate,
    GraduateProjection,
    GraduateTrend,
    RankingUniversidadesNacional,
    RankingUniversidadesRegional,
    Source,
)
from app.schemas.analytics import (
    GraduateInstitutions,
    GraduateProjectionItem,
    GraduatesByYear,
    GraduateSeries,
    GraduateTotals,
    GraduateTrendItem,
    GraduateTrends,
    GraduateYearItem,
    InstitutionCareers,
    InstitutionItem,
    UniversityGraduates,
    UniversityGraduatesItem,
    UniversityRanking,
    UniversityRankingItem,
)
from app.schemas.observatory import (
    CrosswalkCareer,
    CrosswalkOccupation,
    CrosswalkReview,
    IscoLevel,
    SourceRef,
)

router = APIRouter(prefix="/graduates", tags=["graduates"])


def _graduates_country(country: str | None, pais: str | None) -> str | None:
    """The analytics team's tables store the country as a lowercase name ("chile"): ISO3 codes
    are translated with the catalog."""
    if country:
        match = next((c for c in catalog().countries if c.iso3 == country.upper()), None)
        return normalize_text(match.name_es) if match else country.lower()
    return pais.lower() if pais else None


@router.get("/trends", response_model=GraduateTrends)
def graduate_trends(
    country: str | None = Query(None, description="ISO3 (ARG, URY, CHL)"),
    pais: str | None = Query(None, description="Igual que country (se mantiene por compatibilidad)"),
    tendencia: str | None = None,
    session: Session = Depends(get_session),
):
    stmt = select(GraduateTrend).order_by(GraduateTrend.pais, GraduateTrend.nombre)
    if key := _graduates_country(country, pais):
        stmt = stmt.where(GraduateTrend.pais == key)
    if tendencia:
        stmt = stmt.where(GraduateTrend.tendencia == tendencia)
    return GraduateTrends(
        items=[GraduateTrendItem.model_validate(r) for r in session.scalars(stmt).all()]
    )


@router.get("/projections", response_model=list[GraduateProjectionItem])
def graduate_projections(
    country: str | None = Query(None, description="ISO3 (ARG, URY, CHL)"),
    pais: str | None = Query(None, description="Igual que country (se mantiene por compatibilidad)"),
    nombre: str | None = None,
    session: Session = Depends(get_session),
):
    stmt = select(GraduateProjection).order_by(
        GraduateProjection.pais, GraduateProjection.nombre, GraduateProjection.anio
    )
    if key := _graduates_country(country, pais):
        stmt = stmt.where(GraduateProjection.pais == key)
    if nombre:
        stmt = stmt.where(GraduateProjection.nombre == nombre)
    return session.scalars(stmt).all()


def isco_levels(code: str) -> list[IscoLevel]:
    labels = app_config().isco_levels
    return [IscoLevel(level=len(c), level_label=labels[len(c)], code=c, name=name)
            for c, name in catalog().hierarchy(code)]


CSV_COLUMNS = ["carrera", "nivel", "area", "subarea", "titulados", "anio", "crecimiento_anual",
               "generica", "cine_f", "campo_cine_f", "tecnica", "ciuo", "ocupacion", "proporcion", "gran_grupo", "subgrupo_principal",
               "subgrupo"]


def _career_row(career, level, key, fields, series, year, growth, codes,
                cine: dict | None = None) -> CrosswalkCareer:
    return CrosswalkCareer(
        cine_f=(cine or {}).get("code"), cine_f_name=(cine or {}).get("name"),
        technical=(cine or {}).get("technical"),
        career=career, level=level, field_area=fields.get(key, (None, None))[0],
        field_subarea=fields.get(key, (None, None))[1],
        graduates=series.get(year) if year else None, graduates_year=year,
        graduates_growth=growth, is_generic=not codes,
        occupations=[CrosswalkOccupation(
            occupation_code=c, name=catalog().occupation(c).name, share=1 / len(codes),
            hierarchy=isco_levels(c)) for c in codes],
    )


@router.get("/series", response_model=GraduateSeries)
def graduate_series(
    nombre: str,
    country: str | None = Query(None, description="ISO3 (ARG, CHL)"),
    pais: str | None = Query(None, description="Igual que country (se mantiene por compatibilidad)"),
    session: Session = Depends(get_session),
):
    """Observed graduates per year of one career; its projection is in /graduates/projections."""
    key = _graduates_country(country, pais)
    points = career_points(session, key, nombre) if key else None
    if points is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            app_config().messages["unknown_graduate_series"].format(name=nombre))
    return GraduateSeries(pais=key, nombre=nombre, puntos=points)


@router.get("/institutions/list", response_model=list[InstitutionItem])
def graduate_institution_list(
    country: str | None = Query(None, description="ISO3 (ARG, CHL, URY)"),
    session: Session = Depends(get_session),
):
    """Institutions with graduates per career, for a filter."""
    return institution_list(session, _graduates_country(country, None))


@router.get("/institutions/careers", response_model=InstitutionCareers)
def graduate_institution_careers(
    institucion: str,
    country: str | None = Query(None, description="ISO3 (ARG, CHL, URY)"),
    session: Session = Depends(get_session),
):
    """One institution's graduates per career and year. Projections are per career in the whole
    country, so they are not part of this."""
    return InstitutionCareers(institucion=institucion, carreras=institution_careers(
        session, institucion, _graduates_country(country, None)))


@router.get("/institutions", response_model=GraduateInstitutions)
def graduate_institutions(
    nombre: str,
    country: str | None = Query(None, description="ISO3 (ARG, CHL)"),
    pais: str | None = Query(None, description="Igual que country (se mantiene por compatibilidad)"),
    session: Session = Depends(get_session),
):
    """Graduates of one career per institution and year, largest first. Empty where the source
    does not publish them by institution (Argentina)."""
    key = _graduates_country(country, pais)
    return GraduateInstitutions(pais=key or "", nombre=nombre, **career_institutions(session, key, nombre))


@router.get("/totals", response_model=GraduateTotals)
def graduate_totals(
    sector: str | None = Query(None, description="sector_code del catálogo, u 'otros'"),
    tema: str | None = None,
    session: Session = Depends(get_session),
):
    """Observed graduates per country and year of the careers that match. Without a topic it adds up
    careers of the source only: programs found by topic are part of them and also count diplomas."""
    return GraduateTotals(**totals_by_country(session, sector, tema))


@router.get("/by-year", response_model=GraduatesByYear)
def graduates_by_year(
    year: int | None = Query(None, description="Año; sin él, solo los años disponibles"),
    country: str | None = Query(None, description="ISO3 (ARG, CHL)"),
    session: Session = Depends(get_session),
):
    """Graduates per career in a year: observed where published, indicative projection after that."""
    observed, projected = available_years(session)
    items = values_for_year(session, year, _graduates_country(country, None)) if year else []
    return GraduatesByYear(anio=year, anios_observados=observed, anios_proyectados=projected,
                           items=[GraduateYearItem(**i) for i in items])


@router.get("/universities", response_model=UniversityGraduates)
def university_graduates(
    country: str | None = Query(None, description="ISO3 del país"),
    year: int | None = None,
    session: Session = Depends(get_session),
):
    """Graduates per institution and year, as each official source publishes them. Most graduates
    first within each year; latest year first."""
    p = analytics_params("universities")
    stmt = select(FactInstitucionesEgresados).order_by(
        FactInstitucionesEgresados.anio.desc(), FactInstitucionesEgresados.graduados.desc(),
        FactInstitucionesEgresados.institucion)
    if country:
        stmt = stmt.where(FactInstitucionesEgresados.pais == country.upper())
    if year:
        stmt = stmt.where(FactInstitucionesEgresados.anio == year)
    rows = session.scalars(stmt.limit(p["max_rows"])).all()
    return UniversityGraduates(total=len(rows), nota=p["note"], items=[UniversityGraduatesItem(
        pais=r.pais, institucion=r.institucion, tipo_gestion=r.tipo_gestion,
        tipo_institucion=r.tipo_institucion, anio=r.anio, graduados=r.graduados,
        nivel=p["levels"][r.pais], es_observado=r.es_observado, fuente_id=r.fuente_id)
        for r in rows])


@router.get("/universities/ranking", response_model=UniversityRanking)
def university_ranking(
    alcance: Literal["regional", "nacional"] = "regional",
    country: str | None = Query(None, description="ISO3 del país (solo alcance nacional)"),
    session: Session = Depends(get_session),
):
    """Universities with the most graduates: the regional top in the last year all three countries
    have, or each country's top in its latest year."""
    p = analytics_params("universities")
    if alcance == "regional":
        rows = session.scalars(select(RankingUniversidadesRegional).order_by(
            RankingUniversidadesRegional.ranking_regional)).all()
        items = [(r.ranking_regional, r) for r in rows]
        criterio = p["regional_criterion"]
    else:
        stmt = select(RankingUniversidadesNacional).order_by(
            RankingUniversidadesNacional.pais, RankingUniversidadesNacional.ranking_nacional)
        if country:
            stmt = stmt.where(RankingUniversidadesNacional.pais == country.upper())
        items = [(r.ranking_nacional, r) for r in session.scalars(stmt).all()]
        criterio = p["coverage"]
    return UniversityRanking(alcance=alcance, criterio=criterio, nota=p["note"], items=[
        UniversityRankingItem(posicion=pos, pais=r.pais, institucion=r.institucion,
                              tipo_gestion=r.tipo_gestion, anio=r.anio_evaluado,
                              graduados=r.graduados, nivel=r.periodo_detalle)
        for pos, r in items])


@router.get("/crosswalk", response_model=CrosswalkReview)
def crosswalk_review(
    country: str = Query(..., description="ISO3 del país con correspondencia (hoy: CHL)"),
    format: Literal["json", "csv"] = "json",
    session: Session = Depends(get_session),
):
    """Career -> occupation correspondence used for the supply side of skill gaps, for review:
    each career with its latest graduates, growth and the CIUO-08 occupations it maps to (name
    and hierarchy). Most graduates first. format=csv: one row per career and occupation."""
    p = analytics_params("skill_gaps")
    path = p["crosswalks"].get(country.upper())
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, app_config().messages[
            "no_crosswalk"].format(country=country.upper()))
    cw = load_crosswalk(path)
    levels = crosswalk_levels(cw)
    rows = session.scalars(select(Graduate).where(Graduate.country_iso3 == country.upper(),
                                                  Graduate.level.in_(levels))).all()
    by_career: dict[tuple, dict[int, float]] = {}
    fields: dict[str, tuple] = {}
    for g in rows:
        by_career.setdefault((g.career_key, g.level), {})[g.year] = g.graduates
        fields[g.career_key] = (g.field_area, g.field_subarea)
    conf = supply_growth_conf(p)
    max_age = analytics_params("employability")["max_age_years"]
    items = []
    for career, entry in cw["careers"].items():
        key = normalize_text(career)
        # one row per level with data (or per level the row names explicitly)
        row_levels = [lv for lv in levels if (key, lv) in by_career] or levels[:1]
        for level in row_levels:
            series = by_career.get((key, level), {})
            year = max(series) if series else None
            growth = dimension_value([Point(y, v, "g", None) for y, v in sorted(series.items())],
                                     conf, year, max_age)[0] if series else None
            codes = crosswalk_codes(entry, level)
            cine = cw.get("cine", {}).get(career)
            if cine is not None:  # technical by name or by level
                cine = {**cine, "technical": cine["technical"]
                        or level in (cw.get("technical_levels") or [])}
            items.append(_career_row(career, level, key, fields, series, year, growth, codes,
                                     cine))
    items.sort(key=lambda i: (-(i.graduates or 0), i.career, i.level))

    total = sum(i.graduates or 0 for i in items)
    mapped_total = sum(i.graduates or 0 for i in items if not i.is_generic)
    source = session.scalar(select(Source).where(Source.source_code == profiles()[
        cw["source_profile"]].source))
    review = CrosswalkReview(
        country_iso3=country.upper(), reviewed=bool(cw.get("reviewed")), file=path,
        levels=levels, via=cw.get("via"), source=SourceRef(code=source.source_code, name=source.name)
        if source else None, careers=len(items), mapped=sum(not i.is_generic for i in items),
        generic=sum(i.is_generic for i in items),
        graduates_mapped_share=mapped_total / total if total else None, items=items)
    if format == "json":
        return review
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_COLUMNS)
    for i in items:
        base = [i.career, i.level, i.field_area, i.field_subarea, i.graduates, i.graduates_year,
                None if i.graduates_growth is None else round(i.graduates_growth, 4),
                "si" if i.is_generic else "no", i.cine_f, i.cine_f_name,
                None if i.technical is None else ("si" if i.technical else "no")]
        if not i.occupations:
            writer.writerow(base + [None] * 6)
        for o in i.occupations:
            names = {lv.level: lv.name for lv in o.hierarchy}
            writer.writerow(base + [o.occupation_code, o.name, round(o.share, 3), names.get(1),
                                    names.get(2), names.get(3)])
    filename = f"correspondencia_carreras_ciuo_{country.lower()}.csv"
    return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
