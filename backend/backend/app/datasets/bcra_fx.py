"""Official US dollar, daily: the wholesale quote of the Banco Central de la República Argentina
(public API, sources.yaml -> bcra_dolar).

Each run asks for the days since the last one stored, plus a few more in case a quote was
corrected: what changes goes to data_revisions. Argentina's monthly wages (cep_xxi.py) are converted
with the average of each month, so a year with missing months can be shown in dollars too.
"""
import json
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.http import download_sync
from app.core.config_files import SourceConf, sources
from app.ingestion.revisions import record_changes
from app.models import IngestionRun, Source, TipoCambioDiario


def read_page(body: dict, currency: str) -> dict[date, float]:
    return {date.fromisoformat(r["fecha"]): float(d["tipoCotizacion"])
            for r in body["results"] for d in r["detalle"]
            if d["codigoMoneda"] == currency and d["tipoCotizacion"] > 0}


def fetch_rates(conf: SourceConf, start: date, end: date) -> dict[date, float]:
    """Year by year and page by page; days without a quote are simply absent."""
    o, out = conf.options, {}
    headers = {"User-Agent": sources().http.user_agent}
    for year in range(start.year, end.year + 1):
        first, last, offset = max(start, date(year, 1, 1)), min(end, date(year, 12, 31)), 0
        while True:
            body = json.loads(download_sync(
                f"{conf.base_url}/Cotizaciones/{o['currency']}?fechadesde={first}&fechahasta={last}"
                f"&limit={o['page_size']}&offset={offset}", o["max_bytes"], headers))
            out.update(read_page(body, o["currency"]))
            offset += len(body["results"])
            if not body["results"] or offset >= body["metadata"]["resultset"]["count"]:
                break
    return out


def load_rates(session: Session, rates: dict[date, float], currency: str, source_id: int,
               run_id: int | None) -> int:
    """Add the new days and update the corrected ones, logging them. Returns the revisions logged."""
    stored = {r.fecha: r for r in session.scalars(select(TipoCambioDiario).where(
        TipoCambioDiario.moneda == currency, TipoCambioDiario.fecha.in_(rates))).all()}
    revisions = record_changes(
        session, TipoCambioDiario.__tablename__, source_id, run_id, ["moneda", "fecha"],
        {(currency, day): (r.valor, None) for day, r in stored.items()},
        {(currency, day): value for day, value in rates.items()}, removals=False)
    for day, value in rates.items():
        if day in stored:
            stored[day].valor = value
        else:
            session.add(TipoCambioDiario(moneda=currency, fecha=day, valor=value, source_id=source_id))
    session.flush()
    return revisions


def run_bcra_source(session: Session, source_code: str, run: IngestionRun) -> tuple[int, list[str]]:
    """Returns (days read, warnings)."""
    conf = sources().get(source_code)
    o = conf.options
    source = session.scalar(select(Source).where(Source.source_code == source_code))
    last = session.scalar(select(func.max(TipoCambioDiario.fecha)).where(TipoCambioDiario.moneda == o["currency"]))
    start = last - timedelta(days=o["overlap_days"]) if last else date(o["first_year"], 1, 1)
    rates = fetch_rates(conf, start, date.today())
    load_rates(session, rates, o["currency"], source.source_id, run.run_id)
    return len(rates), []


def monthly_rates(session: Session, currency: str) -> dict[str, float]:
    """{YYYY-MM: average of the month's quotes}."""
    days: dict[str, list[float]] = defaultdict(list)
    for day, value in session.execute(select(TipoCambioDiario.fecha, TipoCambioDiario.valor).where(
            TipoCambioDiario.moneda == currency)).all():
        days[day.isoformat()[:7]].append(value)
    return {month: sum(values) / len(values) for month, values in days.items()}


def latest_rate(session: Session, currency: str, today: date | None = None) -> TipoCambioDiario | None:
    """The quote of the last business day before today: today's may not be final yet."""
    return session.scalar(select(TipoCambioDiario).where(
        TipoCambioDiario.moneda == currency, TipoCambioDiario.fecha < (today or date.today()))
        .order_by(TipoCambioDiario.fecha.desc()).limit(1))
