import csv
import io
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.employability_run import Point, dimension_value
from app.analytics.skill_gaps_run import (
    crosswalk_codes,
    crosswalk_levels,
    load_crosswalk,
    supply_growth_conf,
)
from app.core.config_files import analytics_params, app_config, catalog
from app.core.database import get_session
from app.datasets.profiles import normalize_text, profiles
from app.models import Graduate, GraduateProjection, GraduateTrend, Source
from app.schemas.analytics import GraduateProjectionItem, GraduateTrendItem, GraduateTrends
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
               "generica", "ciuo", "ocupacion", "proporcion", "gran_grupo", "subgrupo_principal",
               "subgrupo"]


def _career_row(career, level, key, fields, series, year, growth, codes) -> CrosswalkCareer:
    return CrosswalkCareer(
        career=career, level=level, field_area=fields.get(key, (None, None))[0],
        field_subarea=fields.get(key, (None, None))[1],
        graduates=series.get(year) if year else None, graduates_year=year,
        graduates_growth=growth, is_generic=not codes,
        occupations=[CrosswalkOccupation(
            occupation_code=c, name=catalog().occupation(c).name, share=1 / len(codes),
            hierarchy=isco_levels(c)) for c in codes],
    )


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
            items.append(_career_row(career, level, key, fields, series, year, growth, codes))
    items.sort(key=lambda i: (-(i.graduates or 0), i.career, i.level))

    total = sum(i.graduates or 0 for i in items)
    mapped_total = sum(i.graduates or 0 for i in items if not i.is_generic)
    source = session.scalar(select(Source).where(Source.source_code == profiles()[
        cw["source_profile"]].source))
    review = CrosswalkReview(
        country_iso3=country.upper(), reviewed=bool(cw.get("reviewed")), file=path,
        levels=levels, source=SourceRef(code=source.source_code, name=source.name)
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
                "si" if i.is_generic else "no"]
        if not i.occupations:
            writer.writerow(base + [None] * 6)
        for o in i.occupations:
            names = {lv.level: lv.name for lv in o.hierarchy}
            writer.writerow(base + [o.occupation_code, o.name, round(o.share, 3), names.get(1),
                                    names.get(2), names.get(3)])
    filename = f"correspondencia_carreras_ciuo_{country.lower()}.csv"
    return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
