"""KPIs per sector: fills the team's analytic tables from official data we already hold.

reporte_densidad_profesional_sector, hecho_ocupacion_terciarios, hecho_salario (ILOSTAT),
analisis_genero_integral and proyecciones_graduados_sector are derived: they are rebuilt from the
graduates tables and the ILOSTAT series on each recalculation, and what changes in those sources
stays in data_revisions. Settings: analytics.yaml -> sector_kpis.
"""
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics.graduate_trends_run import all_series, career_name, career_sectors
from app.analytics.projections import project_series
from app.core.config_files import analytics_params, catalog
from app.datasets.bcra_fx import latest_rate
from app.datasets.profiles import normalize_text
from app.models import (
    AnalisisGeneroIntegral,
    FactEgresados,
    FactOcupacionTerciarios,
    FactoresMacroPPA,
    FactSalario,
    Observation,
    ProyeccionesGraduadosSector,
    ReporteDensidadProfesional,
)

MONTHS_IN_YEAR = 12


def _sector_names() -> dict[str | None, str]:
    conf = analytics_params("sector_kpis")
    return {**{s.sector_code: s.name for s in catalog().sectors}, None: conf["total_label"]}


def _iso() -> dict[str, str]:
    """Country key of the trend tables ("chile") -> ISO3."""
    return {normalize_text(c.name_es): c.iso3 for c in catalog().countries}


def _annual(session: Session, indicator: str) -> dict[tuple[str, str | None, int], float]:
    """{(country, sector, year): value} of an annual observed series; sector None is the total."""
    rows = session.execute(select(
        Observation.country_iso3, Observation.sector_code, Observation.period_start, Observation.value,
    ).where(Observation.indicator_code == indicator, Observation.data_type == "observed",
            Observation.frequency == "A", Observation.occupation_code.is_(None))).all()
    return {(c, s, p.year): v for c, s, p, v in rows}


def graduates_by_sector(series: list) -> dict[tuple[str, str | None, int], float]:
    """Careers of the source per sector and year, and the country total. Programs found by topic
    are left out: they are part of the careers and also count diplomas."""
    iso = _iso()
    totals: dict[tuple[str, str | None, int], float] = defaultdict(float)
    for s in series:
        if s.tracked:
            continue
        for year, value in s.by_year.items():
            if value > 0:
                totals[(iso[s.pais], None, year)] += value
                if s.sector:
                    totals[(iso[s.pais], s.sector, year)] += value
    return totals


def density_rows(graduates: dict, employment: dict) -> list[dict]:
    """Graduates per 1,000 employed. Employment comes in thousands of persons."""
    conf = analytics_params("sector_kpis")
    names = _sector_names()
    out = []
    for (country, sector, year), value in graduates.items():
        employed = employment.get((country, sector, year))
        if not employed:
            continue
        out.append({
            "pais": country, "sector": names[sector], "anio": year, "graduados_anuales": value,
            "puestos_empleo": employed * 1000, "graduados_por_mil_ocupados": round(value / employed, 2),
            "ratio_graduados_vs_empleo_pct": round(value / employed / 10, 3),
            "fuente_graduados": conf["graduates_source"][country], "fuente_empleo": conf["ilostat_source"],
            "concepto": conf["density_concept"]})
    return out


def employment_rows(employment: dict, women: dict) -> list[dict]:
    conf = analytics_params("sector_kpis")
    names = _sector_names()
    out = []
    for (country, sector, year), value in employment.items():
        female = women.get((country, sector, year))
        out.append({
            "pais": country, "fuente_id": conf["ilostat_source"], "sector": names[sector], "anio": year,
            "puestos_empleo": value * 1000, "meses_observados": 12, "es_observado": True,
            "share_mujeres": round(female / value * 100, 2) if female is not None and value else None})
    return out


def earnings_rows(total: dict, women: dict, men: dict) -> list[dict]:
    conf = analytics_params("sector_kpis")
    names = _sector_names()
    return [{"pais": country, "fuente_id": conf["ilostat_source"], "sector": names[sector], "anio": year,
             "sexo": sex, "salario_usd_ppa": value, "tipo_salario": conf["earnings_type"],
             "metodo_ppa": conf["earnings_method"], "es_observado": True}
            for sex, series in (("T", total), ("F", women), ("M", men))
            for (country, sector, year), value in series.items()]


def graduates_by_sex(session: Session) -> dict[tuple[str, str | None, int], dict[str, float]]:
    """{(country, sector, year): {F, M, NB}}. Sector None is the country total; a country that only
    publishes sex for the whole country (Argentina) has no sector rows."""
    tracked = analytics_params("tracked_careers")
    trends = analytics_params("graduate_trends")
    sectors = career_sectors()
    totals: dict[tuple[str, str | None, int], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    rows = session.execute(select(
        FactEgresados.pais, FactEgresados.carrera_objetivo, FactEgresados.anio, FactEgresados.sexo,
        FactEgresados.valor).where(FactEgresados.nivel_granularidad == tracked["sex_granularity"])).all()
    for country, career, year, sex, value in rows:
        totals[(country, None, year)][sex] += value or 0.0
        if career:
            name = career_name(career, trends["countries"][country], trends)
            sector = sectors.get(country, {}).get(normalize_text(name))
            if sector:
                totals[(country, sector, year)][sex] += value or 0.0
    return totals


def parity_label(pct_women: float, people: float | None = None) -> str:
    conf = analytics_params("sector_kpis")
    low, high = conf["parity_band"]
    labels = conf["parity_labels"]
    if people is not None and people < conf["parity_min_people"]:
        return labels["few"]
    return labels["parity"] if low <= pct_women <= high else labels["women" if pct_women > high else "men"]


def gender_rows(by_sex: dict, employment: dict, women: dict) -> list[dict]:
    conf = analytics_params("sector_kpis")
    names = _sector_names()
    out = []
    for (country, sector, year), sexes in by_sex.items():
        total = sum(sexes.values())
        if not total:
            continue
        pct = round(sexes.get("F", 0.0) / total * 100, 2)
        male = round(sexes.get("M", 0.0) / total * 100, 2)
        employed, female = employment.get((country, sector, year)), women.get((country, sector, year))
        share = round(female / employed * 100, 2) if employed and female is not None else None
        out.append({
            "pais": country, "sector": names[sector], "periodo_graduados": str(year),
            "f": sexes.get("F", 0.0), "m": sexes.get("M", 0.0), "nb": sexes.get("NB", 0.0),
            "total_graduados": total, "pct_mujeres_graduadas": pct, "pct_varones_graduados": male,
            "pct_nb_graduados": round(sexes.get("NB", 0.0) / total * 100, 2),
            "brecha_graduados_pct": round(pct - male, 2), "anio_empleo": year if share is not None else None,
            "pct_mujeres_empleadas": share, "brecha_empleo_pct": round(2 * share - 100, 2) if share is not None else None,
            "diagnostico_paridad": parity_label(pct, total),
            "criterio_referencia": conf["parity_criterion"]})
    return out


def projection_rows(graduates: dict) -> list[dict]:
    """Indicative projection per sector, where the series has enough history and no gaps."""
    conf = analytics_params("sector_kpis")
    names = _sector_names()
    by_sector: dict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    for (country, sector, year), value in graduates.items():
        if sector:
            by_sector[(country, sector)][year] = value
    out = []
    for (country, sector), series in by_sector.items():
        years = list(range(min(series), max(series) + 1))
        if any(y not in series for y in years):
            continue
        values = [series[y] for y in years]
        projected = project_series(values)
        for p in projected or []:
            out.append({
                "pais": country, "sector": names[sector], "ultimo_anio_observado": years[-1],
                "ultimo_valor_observado": values[-1], "horizonte_anios": p["step"],
                "anio_proyectado": years[-1] + p["step"], "valor_proyectado": round(p["value"]),
                "limite_inferior_95": max(0, round(p["lower_bound"])), "limite_superior_95": round(p["upper_bound"]),
                "n_puntos_base": len(values), "modelo": conf["projection_model"]})
    return out


def recompute_sector_tables(session: Session) -> int:
    """Rebuild the five tables. Returns the rows stored."""
    series = all_series(session)
    graduates = graduates_by_sector(series)
    employment = _annual(session, "employment")
    women = _annual(session, "employment_women")
    tables = (
        (ReporteDensidadProfesional, density_rows(graduates, employment)),
        (FactOcupacionTerciarios, employment_rows(employment, women)),
        (FactSalario, earnings_rows(_annual(session, "mean_monthly_earnings_ppp"),
                                    _annual(session, "mean_monthly_earnings_ppp_women"),
                                    _annual(session, "mean_monthly_earnings_ppp_men"))),
        (AnalisisGeneroIntegral, gender_rows(graduates_by_sex(session), employment, women)),
        (ProyeccionesGraduadosSector, projection_rows(graduates)),
    )
    stored = 0
    ilostat = analytics_params("sector_kpis")["ilostat_source"]
    for model, rows in tables:
        # these two tables also hold CEP-XXI's rows, which its own job keeps
        scope = [model.fuente_id == ilostat] if model in (FactOcupacionTerciarios, FactSalario) else []
        session.execute(delete(model).where(*scope))
        session.flush()
        session.add_all([model(**r) for r in rows])
        stored += len(rows)
    session.flush()
    return stored


def sector_kpis(session: Session) -> dict:
    """The tables joined per country, sector and year, for the screen."""
    rows: dict[tuple[str, str, int], dict] = defaultdict(dict)
    for r in session.scalars(select(ReporteDensidadProfesional)).all():
        rows[(r.pais, r.sector, r.anio)].update(graduados=r.graduados_anuales, densidad=r.graduados_por_mil_ocupados)
    ilostat = analytics_params("sector_kpis")["ilostat_source"]
    for r in session.scalars(select(FactOcupacionTerciarios).where(FactOcupacionTerciarios.fuente_id == ilostat)).all():
        rows[(r.pais, r.sector, r.anio)].update(ocupados=r.puestos_empleo, pct_mujeres_ocupadas=r.share_mujeres)
    field = {"T": "salario_total", "F": "salario_mujeres", "M": "salario_varones"}
    for r in session.scalars(select(FactSalario).where(FactSalario.fuente_id == ilostat)).all():
        rows[(r.pais, r.sector, r.anio)][field[r.sexo]] = r.salario_usd_ppa
    for r in session.scalars(select(AnalisisGeneroIntegral)).all():
        rows[(r.pais, r.sector, int(r.periodo_graduados))].update(
            graduados_con_sexo=r.total_graduados, pct_mujeres_graduadas=r.pct_mujeres_graduadas,
            f=r.f, m=r.m, nb=r.nb, pct_varones_graduados=r.pct_varones_graduados,
            pct_nb_graduados=r.pct_nb_graduados, brecha_graduados_pct=r.brecha_graduados_pct,
            diagnostico_paridad=r.diagnostico_paridad)
    items = []
    for (country, sector, year), values in rows.items():
        women, men = values.get("salario_mujeres"), values.get("salario_varones")
        gap = round((men - women) / men * 100, 1) if women is not None and men else None
        employed = values.get("pct_mujeres_ocupadas")
        items.append({"pais": country, "sector": sector, "anio": year, "brecha_salarial_pct": gap,
                      "brecha_empleo_pct": round(2 * employed - 100, 2) if employed is not None else None,
                      "diagnostico_empleo": parity_label(employed) if employed is not None else None, **values})
    projections = [{"pais": r.pais, "sector": r.sector, "anio": r.anio_proyectado, "valor": r.valor_proyectado,
                    "limite_inferior": r.limite_inferior_95, "limite_superior": r.limite_superior_95}
                   for r in session.scalars(select(ProyeccionesGraduadosSector)).all()]
    return {"items": sorted(items, key=lambda i: (i["pais"], i["sector"], i["anio"])),
            "proyecciones": sorted(projections, key=lambda p: (p["pais"], p["sector"], p["anio"])),
            "nota": analytics_params("sector_kpis")["note"], "genero_nota": analytics_params("sector_kpis")["gender_note"],
            **cep_series(session)}


def cep_series(session: Session) -> dict:
    """Argentina's registered private jobs and salaries (CEP-XXI), with the real salary as an index."""
    conf = analytics_params("cep_xxi")
    prices = {r.anio: r.ipc_original for r in session.scalars(select(FactoresMacroPPA).where(FactoresMacroPPA.pais == "ARG")).all()}
    jobs = {(r.sector, r.anio): r for r in session.scalars(select(FactOcupacionTerciarios).where(
        FactOcupacionTerciarios.fuente_id == conf["source_label"])).all()}
    wages = {(r.sector, r.anio): r for r in session.scalars(select(FactSalario).where(
        FactSalario.fuente_id == conf["source_label"])).all()}
    items = []
    for (sector, year), job in jobs.items():
        wage = wages.get((sector, year))
        nominal = wage.salario_moneda_local if wage else None
        # a year with missing months gets no yearly factor: those factors include months its wages do not
        full_year = job.meses_observados == MONTHS_IN_YEAR
        real = nominal / prices[year] if full_year and nominal and prices.get(year) else None
        base_wage = wages.get((sector, conf["real_base_year"]))
        base = base_wage.salario_moneda_local / prices[conf["real_base_year"]] \
            if base_wage and prices.get(conf["real_base_year"]) else None
        items.append({"sector": sector, "anio": year, "puestos": job.puestos_empleo, "meses": job.meses_observados,
                      "pct_mujeres": job.share_mujeres, "salario_ars": nominal,
                      "salario_usd": wage.salario_usd if wage else None,
                      "salario_usd_ppa": wage.salario_usd_ppa if wage else None,
                      "indice_real": round(real / base * 100, 1) if real and base else None})
    latest = latest_rate(session, conf["fx_currency"])
    return {"cep_xxi": sorted(items, key=lambda i: (i["sector"], i["anio"])), "cep_nota": conf["note"],
            "cep_base": conf["real_base_year"],
            "dolar_oficial": {"nombre": conf["fx_label"], "fecha": latest.fecha, "valor": latest.valor} if latest else None}
