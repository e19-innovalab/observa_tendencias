"""Trends and indicative projections per career, from the official graduates table.

One series per country and career, with the levels and sources of analytics.yaml ->
graduate_trends, plus the tracked careers grouped from official program names. Each country-year
uses one source, so a year published by two is not counted twice. Recalculated after each load;
what changes in the source stays in data_revisions.
"""
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

import yaml
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics.projections import project_series
from app.analytics.trends import classify_trend
from app.core.config import settings
from app.core.config_files import analytics_params, catalog
from app.datasets.profiles import normalize_text
from app.models import FactEgresados, Graduate, GraduateProjection, GraduateTrend, Source


@dataclass
class GraduateRow:
    country: str
    career_key: str
    career: str
    level: str
    year: int
    value: float
    source: str


@dataclass
class CareerSeries:
    pais: str
    nombre: str
    by_year: dict[int, float]
    last_year: int  # the country's latest year: a career that stopped before it has gaps
    tracked: bool = False  # a program found by topic (app/datasets/tracked_careers.py)
    sector: str | None = None  # catalog sector_code; None: other activities
    tema: str | None = None


def _country_key(iso3: str) -> str:
    """The trend tables store the country as a lowercase name ("chile")."""
    return normalize_text(next(c.name_es for c in catalog().countries if c.iso3 == iso3))


@lru_cache
def _names_table(path: str) -> tuple[list[tuple[re.Pattern, str]], dict[str, str]]:
    """(rules, normalized name -> final name) of a file of name matches."""
    with (settings.config_dir / path).open(encoding="utf-8") as f:
        table = yaml.safe_load(f)
    rules = [(re.compile(pattern, re.I), replacement) for pattern, replacement in table["reglas"]]
    return rules, {form: final for final, forms in table["equivalencias"].items() for form in forms}


def career_name(published: str, country: dict, conf: dict) -> str:
    """The name a career goes by: as published without footnote marks, or through the country's
    file of matches when its source renames careers between years."""
    name = published.rstrip(conf["name_marks"]).strip()
    if "names_file" not in country:
        return name
    rules, finals = _names_table(country["names_file"])
    for pattern, replacement in rules:
        name = pattern.sub(replacement, name).strip()
    return finals.get(normalize_text(name), name)


def career_series(rows: Iterable[GraduateRow], conf: dict) -> list[CareerSeries]:
    """Add up each career's selected levels per year, taking each country-year from the first
    source in the configured order that has it."""
    usable = defaultdict(list)
    skip = set(conf["skip_careers"])
    for r in rows:
        country = conf["countries"].get(r.country)
        if country and r.level in country["levels"] and r.source in country["sources"]:
            name = career_name(r.career, country, conf)
            key = normalize_text(name)
            if key not in skip:
                r.career = name
                usable[(r.country, r.year, r.source)].append((key, r))
    chosen: dict[tuple[str, int], str] = {}
    for country, year, source in usable:
        order = conf["countries"][country]["sources"]
        current = chosen.get((country, year))
        if current is None or order.index(source) < order.index(current):
            chosen[(country, year)] = source
    values: dict[tuple[str, str], dict[int, float]] = defaultdict(lambda: defaultdict(float))
    names: dict[tuple[str, str], tuple[int, str]] = {}
    latest: dict[str, int] = {}
    for (country, year), source in chosen.items():
        latest[country] = max(latest.get(country, year), year)
        for key, r in usable[(country, year, source)]:
            values[(country, key)][year] += r.value
            if year >= names.get((country, key), (0, ""))[0]:
                names[(country, key)] = (year, r.career)
    return [CareerSeries(_country_key(country), names[(country, key)][1], dict(by_year), latest[country])
            for (country, key), by_year in values.items()]


def analyze(series: CareerSeries) -> tuple[dict, list[dict]] | None:
    """(trend row, projection rows). Years before the first with graduates are not data; a later
    year without graduates is a gap, which blocks the projection and a trend whose window has it."""
    started = [y for y, v in series.by_year.items() if v > 0]
    if not started:
        return None
    first = min(started)
    values = [series.by_year.get(y, 0.0) for y in range(first, series.last_year + 1)]
    window = values[-analytics_params("trends")["window_points"]:]
    result = classify_trend(window)
    has_gaps = 0 in values
    if 0 in window:  # growth rates would divide by a year without graduates
        result = {"slope": None, "pct_change": None, "trend_state": "insufficient_data"}
    projected = None if has_gaps else project_series(values)
    min_points = analytics_params("projections")["min_points"]
    status = "generada" if projected else (
        "con_huecos" if has_gaps else f"historia_insuficiente(<{min_points})")
    trend = {
        "pais": series.pais, "nombre": series.nombre, "anio_desde": first,
        "anio_hasta": series.last_year, "n_anios_serie": len(values), "ventana_anios": len(window),
        "graduados_inicio_ventana": int(window[0]), "graduados_ultimo": int(window[-1]),
        "pendiente_normalizada": result["slope"],
        "variacion_ventana_pct": None if result["pct_change"] is None
        else round(result["pct_change"] * 100, 2),
        "tendencia": result["trend_state"], "tiene_huecos": has_gaps, "proyeccion": status,
        "es_seguimiento": series.tracked, "sector": series.sector, "tema": series.tema,
    }
    projections = [{
        "pais": series.pais, "nombre": series.nombre, "anio": series.last_year + p["step"],
        "graduados_proyectado": round(p["value"]),
        "limite_inferior": max(0, round(p["lower_bound"])),  # there are no negative graduates
        "limite_superior": round(p["upper_bound"]),
    } for p in projected or []]
    return trend, projections


@lru_cache
def career_sectors() -> dict[str, dict[str, str]]:
    """Country -> normalized career -> sector_code, through each career's CINE-F field. A career
    whose field is in no sector is not listed."""
    conf = analytics_params("graduate_trends")
    with (settings.config_dir / conf["sector_file"]).open(encoding="utf-8") as f:
        by_field = {field: sector for sector, fields in yaml.safe_load(f)["sectors"].items()
                    for field in fields}
    out: dict[str, dict[str, str]] = {}
    for iso, country in conf["countries"].items():
        path = settings.config_dir / analytics_params("skill_gaps")["crosswalks"][iso]
        with path.open(encoding="utf-8") as f:
            careers = yaml.safe_load(f)["careers"]
        out[iso] = {}
        for name, entry in careers.items():  # forms of one career: the file's first with a sector
            if entry.get("cine") in by_field:
                out[iso].setdefault(normalize_text(career_name(name, country, conf)), by_field[entry["cine"]])
    return out


def tracked_series(rows: Iterable[tuple], topics: dict[str, str]) -> list[CareerSeries]:
    """rows: (country, program, year, value, sector_code, topic id), all levels added up."""
    values: dict[tuple[str, str], dict[int, float]] = defaultdict(lambda: defaultdict(float))
    labels: dict[tuple[str, str], tuple] = {}
    latest: dict[str, int] = {}
    for country, name, year, value, sector, topic in rows:
        values[(country, name)][year] += value
        labels[(country, name)] = (sector, topics.get(topic))
        latest[country] = max(latest.get(country, year), year)
    return [CareerSeries(_country_key(country), name, dict(by_year), latest[country], tracked=True,
                         sector=labels[(country, name)][0], tema=labels[(country, name)][1])
            for (country, name), by_year in values.items()]


def all_series(session: Session) -> list[CareerSeries]:
    """Careers of the graduates table, with their sector, and programs found by topic. A program
    named like a career of its country is that career: the career stays and takes the topic, so
    one name never means two series."""
    rows = session.execute(select(
        Graduate.country_iso3, Graduate.career_key, Graduate.career, Graduate.level, Graduate.year,
        Graduate.graduates, Source.source_code).join(Source, Source.source_id == Graduate.source_id)).all()
    conf = analytics_params("tracked_careers")
    trends_conf = analytics_params("graduate_trends")
    careers = career_series([*(GraduateRow(*r) for r in rows), *_yearbook_rows(session, trends_conf, conf)],
                            trends_conf)
    tracked = tracked_series(session.execute(select(
        FactEgresados.pais, FactEgresados.carrera_objetivo, FactEgresados.anio, FactEgresados.valor,
        FactEgresados.sector, FactEgresados.carrera_id,
    ).where(FactEgresados.nivel_granularidad == conf["granularity"])).all(), _topics(conf))
    sectors = {_country_key(c): names for c, names in career_sectors().items()}
    by_name = {}
    for s in careers:
        s.sector = sectors.get(s.pais, {}).get(normalize_text(s.nombre))
        by_name[(s.pais, normalize_text(s.nombre))] = s
    programs = []
    for s in tracked:
        career = by_name.get((s.pais, normalize_text(s.nombre)))
        if career:
            career.tema = s.tema
        else:
            programs.append(s)
    return careers + programs


def _yearbook_rows(session: Session, trends_conf: dict, conf: dict) -> list[GraduateRow]:
    """Careers per year added up from the institution tables of a country's yearbooks."""
    out = []
    for iso, country in trends_conf["countries"].items():
        spec = country.get("yearbook_series")
        if not spec:
            continue
        totals: dict[tuple[str, int], float] = defaultdict(float)
        for career, year, value in session.execute(select(
                FactEgresados.carrera_objetivo, FactEgresados.anio, FactEgresados.valor).where(
                FactEgresados.pais == iso,
                FactEgresados.nivel_granularidad == conf["institution_granularity"])).all():
            if year not in spec["exclude_years"]:
                totals[(career, year)] += value or 0.0
        out += [GraduateRow(iso, normalize_text(career), career, spec["level"], year, value, spec["source"])
                for (career, year), value in totals.items()]
    return out


def _topics(conf: dict) -> dict[str, str]:
    """Topic id -> name, from the file of tracked topics."""
    with (settings.config_dir / conf["file"]).open(encoding="utf-8") as f:
        return {c["id"]: c["nombre"] for c in yaml.safe_load(f)["careers"]}


def values_for_year(session: Session, year: int, country: str | None = None) -> list[dict]:
    """Each career's graduates in a year: observed where published, projected after that."""
    series = [s for s in all_series(session) if not country or s.pais == country]
    observed = {(s.pais, s.nombre): s for s in series if s.by_year.get(year, 0) > 0}
    items = [{"pais": s.pais, "nombre": s.nombre, "anio": year, "graduados": s.by_year[year],
              "tipo": "observado", "es_seguimiento": s.tracked} for s in observed.values()]
    tracked = {(s.pais, s.nombre) for s in series if s.tracked}
    stmt = select(GraduateProjection).where(GraduateProjection.anio == year)
    if country:
        stmt = stmt.where(GraduateProjection.pais == country)
    items += [{"pais": p.pais, "nombre": p.nombre, "anio": year, "graduados": p.graduados_proyectado,
               "tipo": "proyectado", "limite_inferior": p.limite_inferior,
               "limite_superior": p.limite_superior, "es_seguimiento": (p.pais, p.nombre) in tracked}
              for p in session.scalars(stmt).all() if (p.pais, p.nombre) not in observed]
    return sorted(items, key=lambda i: (i["pais"], -i["graduados"], i["nombre"]))


def observed_points(series: CareerSeries) -> list[dict]:
    """Yearly values from the first year with graduates to the country's latest year. A later year
    the source does not list has no graduates, the same reading the trends use."""
    started = [y for y, v in series.by_year.items() if v > 0]
    if not started:
        return []
    return [{"anio": y, "graduados": series.by_year.get(y, 0.0)}
            for y in range(min(started), series.last_year + 1)]


def career_points(session: Session, pais: str, nombre: str) -> list[dict] | None:
    """The observed series of one career; None if there is no such career."""
    found = next((s for s in all_series(session) if s.pais == pais and s.nombre == nombre), None)
    return None if found is None else observed_points(found)


def _institution_rows(session: Session, country: str | None = None) -> Iterable:
    """(country key, normalized career, institution, year, value) of generic careers and programs.
    A program named like a generic career of its country is that career: not counted twice."""
    conf = analytics_params("tracked_careers")
    stmt = select(FactEgresados.pais, FactEgresados.carrera_objetivo, FactEgresados.institucion,
                  FactEgresados.anio, FactEgresados.valor, FactEgresados.nivel_granularidad).where(
        FactEgresados.nivel_granularidad.in_([conf["granularity"], conf["institution_granularity"]]),
        FactEgresados.institucion.is_not(None))
    keys = {c.iso3: _country_key(c.iso3) for c in catalog().countries}
    rows = [(keys[iso], normalize_text(career), institution, year, value, kind)
            for iso, career, institution, year, value, kind in session.execute(stmt).all()
            if value and (country is None or keys[iso] == country)]
    generic = {(r[0], r[1]) for r in rows if r[5] == conf["institution_granularity"]}
    for pais, career, institution, year, value, kind in rows:
        if kind == conf["institution_granularity"] or (pais, career) not in generic:
            yield pais, career, institution, year, value


def institution_summary(session: Session) -> dict[tuple[str, str], tuple[int, str]]:
    """(country, normalized career) -> (institutions, largest one) in its latest year with data."""
    values: dict[tuple[str, str], dict[int, dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(float)))
    for country, career, institution, year, value in _institution_rows(session):
        values[(country, career)][year][institution] += value
    out = {}
    for key, years in values.items():
        latest = years[max(years)]
        out[key] = (len(latest), min(latest, key=lambda i: (-latest[i], i)))
    return out


def career_institutions(session: Session, country: str | None, name: str) -> dict:
    """One career per institution and year, largest first, with the total of each year."""
    wanted = normalize_text(name)
    by_institution: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    totals: dict[int, float] = defaultdict(float)
    for _, career, institution, year, value in _institution_rows(session, country):
        if career == wanted:
            by_institution[institution][year] += value
            totals[year] += value
    institutions = [{"institucion": i, "por_anio": dict(years), "total": sum(years.values())}
                    for i, years in by_institution.items()]
    return {"anios": sorted(totals), "totales": dict(totals),
            "instituciones": sorted(institutions, key=lambda i: (-i["total"], i["institucion"]))}


def institution_list(session: Session, country: str | None = None) -> list[dict]:
    """Every institution with data, by name, and how many careers it has."""
    careers: dict[tuple[str, str], set[str]] = defaultdict(set)
    for pais, career, institution, _, _ in _institution_rows(session, country):
        careers[(pais, institution)].add(career)
    return [{"pais": pais, "institucion": institution, "n_carreras": len(found)}
            for (pais, institution), found in sorted(careers.items(), key=lambda kv: (kv[0][1], kv[0][0]))]


def institution_careers(session: Session, institution: str, country: str | None = None) -> list[dict]:
    """One institution's graduates per career and year, with each career's sector and topic."""
    by_career: dict[tuple[str, str], dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for pais, career, name, year, value in _institution_rows(session, country):
        if name == institution:
            by_career[(pais, career)][year] += value
    trends = {(t.pais, normalize_text(t.nombre)): t for t in session.scalars(select(GraduateTrend)).all()}
    out = []
    for key, years in by_career.items():
        trend = trends.get(key)
        if trend:  # careers without a trend have no graduates in the series, or are not careers
            out.append({"pais": trend.pais, "nombre": trend.nombre, "por_anio": dict(years),
                        "es_seguimiento": trend.es_seguimiento, "sector": trend.sector, "tema": trend.tema})
    return sorted(out, key=lambda c: (c["pais"], c["nombre"]))


def totals_by_country(session: Session, sector: str | None, topic: str | None) -> dict:
    """Observed graduates per country and year of the matching careers. Programs found by topic
    count only when a topic is chosen: they are part of the careers and also count diplomas."""
    other = analytics_params("graduate_trends")["other_sector"]
    totals: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for s in all_series(session):
        if (sector and (s.sector or other) != sector) or (topic and s.tema != topic) \
                or (s.tracked and not topic):
            continue
        for year, value in s.by_year.items():
            if value > 0:
                totals[s.pais][year] += value
    years = sorted({y for by_year in totals.values() for y in by_year})
    return {"anios": years, "paises": [{"pais": p, "por_anio": dict(v)} for p, v in sorted(totals.items())]}


def available_years(session: Session) -> tuple[list[int], list[int]]:
    """(years with observed data, years only projected), oldest first."""
    observed = {y for s in all_series(session) for y, v in s.by_year.items() if v > 0}
    projected = set(session.scalars(select(GraduateProjection.anio).distinct()).all())
    return sorted(observed), sorted(projected - observed)


def recompute_graduate_trends(session: Session) -> int:
    """Replace both tables with what the official data says now. Returns the careers stored."""
    results = [r for r in (analyze(s) for s in all_series(session)) if r]
    summary = institution_summary(session)
    for trend, _ in results:
        trend["n_instituciones"], trend["institucion_principal"] = summary.get(
            (trend["pais"], normalize_text(trend["nombre"])), (None, None))
    session.execute(delete(GraduateProjection))
    session.execute(delete(GraduateTrend))
    session.flush()
    session.add_all([GraduateTrend(**trend) for trend, _ in results])
    session.add_all([GraduateProjection(**p) for _, projections in results for p in projections])
    session.flush()
    return len(results)
