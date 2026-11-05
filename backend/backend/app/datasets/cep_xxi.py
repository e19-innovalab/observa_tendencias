"""Argentina: registered private jobs, salaries and share of women per activity (CEP-XXI), and the
price and purchasing-power factors needed to compare those salaries over time.

The files' links come from CEP-XXI's official pages (analytics.yaml -> cep_xxi) and are downloaded
on each run, since they are updated under the same address; nothing changes if neither they nor the
factors did. Totals per sector and year go to hecho_ocupacion_terciarios and hecho_salario, and what
changes to data_revisions. CEP-XXI marks suppressed cells (statistical secrecy) with -99. A year with
missing months gets no yearly factor: those factors include months its wages do not. Dollars do not
need one: each month is converted with that month's average of the official daily quote (bcra_fx.py).
"""
import csv
import io
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isclose
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.connectors.http import download_sync
from app.core.config_files import analytics_params, app_config, catalog, sources
from app.datasets.bcra_fx import monthly_rates
from app.datasets.ingest import DatasetError, _format_alert, find_download_links, store_file
from app.datasets.profiles import DownloadConf
from app.datasets.reader import Issue, ReadReport
from app.datasets.universities import _DirectInput
from app.ingestion.revisions import TOLERANCE, record_changes
from app.models import (
    DatasetFile,
    FactOcupacionTerciarios,
    FactoresMacroPPA,
    FactSalario,
    IngestionRun,
    Source,
)

MONTHS_IN_YEAR = 12
MACRO_VALUES = ["factor_ppa", "ipc_original", "tipo_cambio"]


@dataclass
class Cell:
    jobs: float | None = None
    mean_wage: float | None = None
    women: float | None = None


def sector_activities() -> dict[str, set[int]]:
    """Sector -> two-digit activities, from the catalog's ISIC codes (J62 -> 62)."""
    return {s.name: {int(re.sub(r"\D", "", code)) for code in s.isic_codes} for s in catalog().sectors}


def read_series(content: bytes, value_column: str, conf: dict) -> dict[tuple[str, int], float]:
    """{(YYYY-MM, activity): value}; suppressed cells are left out."""
    rows = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    if not {conf["date_column"], conf["activity_column"], value_column} <= set(rows.fieldnames or []):
        raise ValueError(f"Faltan columnas, llegaron {rows.fieldnames}")
    out = {}
    for row in rows:
        value = float(row[value_column]) if row[value_column] not in ("", None) else conf["suppressed"]
        if value != conf["suppressed"]:
            out[(row[conf["date_column"]][:7], int(row[conf["activity_column"]]))] = value
    return out


def sector_years(jobs: dict, wages: dict, women: dict, conf: dict, rates: dict[str, float] | None = None) -> list[dict]:
    """One row per sector and year, and the total. Jobs: average of the months. Wages and share of
    women: weighted by each activity's jobs, over the cells where both are published. Dollars: each
    month at its rate ({YYYY-MM: rate}), only if every month with wages has one."""
    rates = rates or {}
    sectors: dict[str, set[int] | None] = {**sector_activities(), conf["total_label"]: None}
    out = []
    for sector, activities in sectors.items():
        months: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        wage_mass: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
        dollar_mass: dict[int, float] = defaultdict(float)
        no_rate: set[int] = set()
        women_mass: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
        for (month, activity), count in jobs.items():
            if activities is not None and activity not in activities:
                continue
            year = int(month[:4])
            months[year][month] += count
            wage = wages.get((month, activity))
            if wage is not None:
                wage_mass[year][0] += wage * count
                wage_mass[year][1] += count
                if month in rates:
                    dollar_mass[year] += wage * count / rates[month]
                else:
                    no_rate.add(year)
            share = women.get((month, activity))
            if share is not None:
                women_mass[year][0] += share * count
                women_mass[year][1] += count
        for year, per_month in months.items():
            wage_total, wage_jobs = wage_mass[year]
            share_total, share_jobs = women_mass[year]
            out.append({
                "sector": sector, "anio": year, "meses": len(per_month),
                "puestos": sum(per_month.values()) / len(per_month),
                "salario": wage_total / wage_jobs if wage_jobs else None,
                "salario_usd": dollar_mass[year] / wage_jobs if wage_jobs and year not in no_rate else None,
                "pct_mujeres": share_total / share_jobs * 100 if share_jobs else None})
    return out


def extend_factors(out: dict, us_prices: dict[int, float], conf: dict) -> None:
    """After a country's last published PPP factor: previous factor x its prices / US prices."""
    for country in {c for c, _ in out}:
        years = sorted(y for c, y in out if c == country and "factor_ppa" in out[(c, y)])
        for year in range(years[-1] + 1, max(y for c, y in out if c == country) + 1) if years else ():
            now, before = out.get((country, year), {}), out.get((country, year - 1), {})
            if not all(v in values for v, values in (("ipc_original", now), ("ipc_original", before), ("factor_ppa", before))):
                break
            if year not in us_prices or year - 1 not in us_prices:
                break
            now["factor_ppa"] = (before["factor_ppa"] * (now["ipc_original"] / before["ipc_original"])
                                 / (us_prices[year] / us_prices[year - 1]))
            now["metodo_ppa"] = conf["ppp_extended_method"]


def macro_rows(ppp: dict, cpi: dict, fx: dict, indec: dict[int, list[float]], conf: dict,
               us_prices: dict[int, float] | None = None) -> list[dict]:
    """factores_macro_ppa: PPP factor, exchange rate and consumer prices per country and year.
    Argentina's prices come from INDEC, as an annual average of the full years since its base month."""
    out = {}
    for (country, year), value in ppp.items():
        out.setdefault((country, year), {})["factor_ppa"] = value
    for (country, year), value in fx.items():
        out.setdefault((country, year), {})["tipo_cambio"] = value
    for (country, year), value in cpi.items():
        if country != "ARG":
            out.setdefault((country, year), {}).update(ipc_original=value, fuente_ipc=conf["world_bank_cpi"]["source"],
                                                       base_original_ipc=conf["world_bank_cpi"]["base"])
    for year, values in indec.items():
        if len(values) == MONTHS_IN_YEAR:
            out.setdefault(("ARG", year), {}).update(ipc_original=sum(values) / MONTHS_IN_YEAR, fuente_ipc=conf["indec_cpi"]["source"],
                                                     base_original_ipc=conf["indec_cpi"]["base"])
    extend_factors(out, us_prices or {}, conf)
    bases = {c: v["ipc_original"] for (c, y), v in out.items() if y == conf["cpi_base_year"] and "ipc_original" in v}
    return [{"pais": country, "anio": year, "metodo_ppa": conf["ppp_method"] if "factor_ppa" in values else None,
             "ipc_base_2016": values["ipc_original"] / bases[country] * 100
             if country in bases and "ipc_original" in values else None, **values}
            for (country, year), values in out.items()]


def _world_bank(indicator: str, conf: dict, countries: list[str] | None = None) -> dict[tuple[str, int], float]:
    """{(ISO3, year): value} of a World Bank indicator; countries without data are absent."""
    codes = countries or [c.iso3 for c in catalog().countries]
    url = conf["world_bank_url"].format(countries=";".join(codes), indicator=indicator)
    body = json.loads(download_sync(url, conf["api_max_bytes"], {"User-Agent": sources().http.user_agent}))
    return {(r["countryiso3code"], int(r["date"])): r["value"] for r in body[1] or [] if r["value"] is not None}


def _indec_cpi(conf: dict) -> dict[int, list[float]]:
    url = conf["indec_cpi"]["url"]
    body = json.loads(download_sync(url, conf["api_max_bytes"], {"User-Agent": sources().http.user_agent}))
    values: dict[int, list[float]] = defaultdict(list)
    for date, value in body["data"]:
        if value is not None:
            values[int(date[:4])].append(value)
    return values


def dollars_differ(session: Session, rows: list[dict], conf: dict) -> bool:
    """A new or corrected quote changed what a wage is worth in dollars."""
    stored = {(s.sector, s.anio): s.salario_usd for s in session.scalars(select(FactSalario).where(
        FactSalario.fuente_id == conf["source_label"])).all()}
    for r in rows:
        new, old = r.get("salario_usd"), stored.get((r["sector"], r["anio"]))
        if (new is None) != (old is None) or (new is not None and not isclose(old, new, rel_tol=TOLERANCE)):
            return True
    return False


def _retired_factors(rows, conf: dict) -> list:
    """Stored factors calculated with a PPP method no longer in use."""
    current = {conf["ppp_method"], conf["ppp_extended_method"]}
    return [m for m in rows if m.factor_ppa is not None and m.metodo_ppa and m.metodo_ppa not in current]


def macro_differs(session: Session, macro: list[dict], conf: dict) -> bool:
    rows = session.scalars(select(FactoresMacroPPA)).all()
    stored = {(m.pais, m.anio): m for m in rows}
    if _retired_factors(rows, conf):
        return True
    for r in macro:
        row = stored.get((r["pais"], r["anio"]))
        for field in MACRO_VALUES:
            new, old = r.get(field), getattr(row, field) if row else None
            if new is not None and (old is None or not isclose(old, new, rel_tol=TOLERANCE)):
                return True
    return False


def store_macro(session: Session, macro: list[dict], source_id: int, run_id: int | None, conf: dict) -> int:
    """Update the factors, logging changes. What a source stops publishing stays as it was, unless
    it was calculated with a method no longer in use: mixing methods would make the years incomparable."""
    stored = {(m.pais, m.anio): m for m in session.scalars(select(FactoresMacroPPA)).all()}
    revisions = sum(record_changes(
        session, FactoresMacroPPA.__tablename__, source_id, run_id, ["pais", "anio", "campo"],
        {(*key, field): (getattr(m, field), None) for key, m in stored.items() if getattr(m, field) is not None},
        {(r["pais"], r["anio"], field): r[field] for r in macro if r.get(field) is not None}, removals=False)
        for field in MACRO_VALUES)
    answered = {(r["pais"], r["anio"]) for r in macro if r.get("factor_ppa") is not None}
    retired = [m for m in _retired_factors(stored.values(), conf) if (m.pais, m.anio) not in answered]
    revisions += record_changes(
        session, FactoresMacroPPA.__tablename__, source_id, run_id, ["pais", "anio", "campo"],
        {(m.pais, m.anio, "factor_ppa"): (m.factor_ppa, None) for m in retired}, {}, removals=True)
    for m in retired:
        m.factor_ppa, m.metodo_ppa = None, None
    for r in macro:
        row = stored.get((r["pais"], r["anio"]))
        if row is None:
            row = FactoresMacroPPA(pais=r["pais"], anio=r["anio"])
            session.add(row)
        for field, value in r.items():
            if value is not None or field == "ipc_base_2016":  # derived: follows the current base
                setattr(row, field, value)
    session.flush()
    return revisions


def load_cep(session: Session, rows: list[dict], macro: list[dict], source_id: int, run_id: int | None,
             conf: dict) -> int:
    """Replace CEP-XXI's rows and update the factors, logging changes. Returns the revisions logged."""
    salaries = session.scalars(select(FactSalario).where(FactSalario.fuente_id == conf["source_label"])).all()
    jobs = session.scalars(select(FactOcupacionTerciarios).where(
        FactOcupacionTerciarios.fuente_id == conf["source_label"])).all()
    new_salaries = {(r["sector"], r["anio"]): r["salario"] for r in rows if r["salario"] is not None}
    new_jobs = {(r["sector"], r["anio"]): r["puestos"] for r in rows}
    revisions = record_changes(
        session, FactSalario.__tablename__, source_id, run_id, ["sector", "anio"],
        {(o.sector, o.anio): (o.salario_moneda_local, None) for o in salaries}, new_salaries, removals=True)
    revisions += record_changes(
        session, FactOcupacionTerciarios.__tablename__, source_id, run_id, ["sector", "anio"],
        {(o.sector, o.anio): (o.puestos_empleo, None) for o in jobs}, new_jobs, removals=True)
    session.execute(delete(FactSalario).where(FactSalario.fuente_id == conf["source_label"]))
    session.execute(delete(FactOcupacionTerciarios).where(FactOcupacionTerciarios.fuente_id == conf["source_label"]))
    session.flush()
    revisions += store_macro(session, macro, source_id, run_id, conf)
    factors = {m.anio: m.factor_ppa for m in session.scalars(
        select(FactoresMacroPPA).where(FactoresMacroPPA.pais == "ARG")).all()}
    for r in rows:
        factor = factors.get(r["anio"]) if r["meses"] == MONTHS_IN_YEAR else None
        if r["salario"] is not None:
            session.add(FactSalario(
                pais="ARG", fuente_id=conf["source_label"], sector=r["sector"], anio=r["anio"], sexo="T",
                salario_moneda_local=r["salario"], moneda_local=conf["currency"], factor_ppa=factor,
                salario_usd=r.get("salario_usd"),
                salario_usd_ppa=r["salario"] / factor if factor else None, tipo_salario=conf["wage_type"],
                metodo_ppa=conf["ppp_method"] if factor else None, es_observado=True))
        session.add(FactOcupacionTerciarios(
            pais="ARG", fuente_id=conf["source_label"], sector=r["sector"], anio=r["anio"], puestos_empleo=r["puestos"],
            share_mujeres=r["pct_mujeres"], meses_observados=r["meses"], es_observado=True))
    session.flush()
    return revisions


def _links(conf: dict) -> list[tuple[str, str]]:
    """(series, url) of each file the official pages link now."""
    out = []
    for name, spec in conf["files"].items():
        source = _DirectInput(spec["page"], DownloadConf(
            link_pattern=spec["link_pattern"], allowed_hosts=conf["allowed_hosts"], max_bytes=conf["max_bytes"]))
        out += [(name, link.url) for link in find_download_links(source)]
    return out


def run_cep_source(session: Session, source_code: str, run: IngestionRun) -> tuple[int, list[str]]:
    """Download, check and load. Returns (rows loaded, warnings); (0, []) if nothing changed."""
    conf = analytics_params("cep_xxi")
    source = session.scalar(select(Source).where(Source.source_code == source_code))
    datasets_conf = app_config().datasets
    last = {d.url: d for d in session.scalars(select(DatasetFile).where(
        DatasetFile.profile_code == conf["dataset_code"], DatasetFile.status == "loaded")).all()}
    contents, datasets = {}, []
    for name, url in _links(conf):
        content = download_sync(url, conf["max_bytes"], {"User-Agent": sources().http.user_agent})
        file_name = Path(urlparse(url).path).name
        path, sha = store_file(content, datasets_conf.path(datasets_conf.raw_dir) / source_code, file_name)
        contents[name] = content
        datasets.append(DatasetFile(
            profile_code=conf["dataset_code"], source_id=source.source_id, origin="download", file_name=file_name,
            url=url, sha256=sha, size_bytes=len(content), stored_path=str(path), status="validated", report={},
            created_at=datetime.now(UTC), run_id=run.run_id))
    macro = macro_rows(_world_bank(conf["ppp_indicator"], conf), _world_bank(conf["world_bank_cpi"]["indicator"], conf),
                       _world_bank(conf["fx_indicator"], conf), _indec_cpi(conf), conf,
                       {y: v for (_, y), v in _world_bank(conf["world_bank_cpi"]["indicator"], conf, [conf["us_iso3"]]).items()})
    same_files = len(last) == len(datasets) and all(d.url in last and last[d.url].sha256 == d.sha256 for d in datasets)
    if same_files:
        datasets = []  # only the factors changed: the files on record stay
    session.add_all(datasets)
    session.flush()
    try:
        series = {name: read_series(contents[name], spec["value_column"], conf) for name, spec in conf["files"].items()}
    except (KeyError, ValueError) as exc:
        for dataset in datasets:
            dataset.status = "format_changed"
        reason = f"{type(exc).__name__}: {exc}"
        if datasets:
            _format_alert(session, datasets[0], source, ReadReport(errors=[Issue(reason)]))
        raise DatasetError(f"{conf['dataset_code']}: {reason}") from exc
    rows = sector_years(series["jobs"], series["mean_wage"], series["women"], conf,
                        monthly_rates(session, conf["fx_currency"]))
    if same_files and not macro_differs(session, macro, conf) and not dollars_differ(session, rows, conf):
        return 0, []  # nothing changed
    load_cep(session, rows, macro, source.source_id, run.run_id, conf)
    if datasets:
        for previous in last.values():
            previous.status = "replaced"
        for dataset in datasets:
            dataset.status, dataset.loaded_at = "loaded", datetime.now(UTC)
        datasets[0].records = len(rows)
    return len(rows), []
