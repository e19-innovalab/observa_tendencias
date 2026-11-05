import json
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config_files import sources
from app.datasets import bcra_fx
from app.datasets.bcra_fx import (
    fetch_rates,
    latest_rate,
    load_rates,
    monthly_rates,
    read_page,
    run_bcra_source,
)
from app.models import Base, DataRevision, IngestionRun, Source, TipoCambioDiario


def _day(day, value, currency="USD"):
    return {"fecha": day, "detalle": [{"codigoMoneda": currency, "tipoPase": 0.0, "tipoCotizacion": value}]}


def _body(results, count=None):
    return json.dumps({"status": 200, "metadata": {"resultset": {"count": count if count is not None else len(results)}},
                       "results": results}).encode()


@pytest.fixture
def session():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=[t.__table__ for t in (Source, IngestionRun, DataRevision, TipoCambioDiario)])
    with Session(engine) as s:
        s.add(Source(source_id=1, source_code="bcra_dolar", name="B", source_kind="api"))
        s.commit()
        yield s


def _run(session):
    run = IngestionRun(source_id=1, started_at=datetime.now(UTC), status="running", triggered_by="test")
    session.add(run)
    session.flush()
    return run


def test_only_usable_quotes_are_read():
    body = {"results": [_day("2023-11-03", 350.1), _day("2023-11-02", 0), _day("2023-11-01", 1.1, "EUR"),
                        {"fecha": "2023-10-31", "detalle": []}]}
    assert read_page(body, "USD") == {date(2023, 11, 3): 350.1}


def test_asks_year_by_year_and_page_by_page(monkeypatch):
    urls = []

    def fake(url, *a, **k):
        urls.append(url)
        if "offset=0" in url and "fechadesde=2022-12-30" in url:
            return _body([_day("2022-12-30", 177.0)], count=2)
        if "fechadesde=2022-12-30" in url:
            return _body([_day("2022-12-29", 176.0)], count=2)
        return _body([_day("2023-01-02", 178.0)])

    monkeypatch.setattr(bcra_fx, "download_sync", fake)
    rates = fetch_rates(sources().get("bcra_dolar"), date(2022, 12, 30), date(2023, 1, 5))
    assert rates == {date(2022, 12, 30): 177.0, date(2022, 12, 29): 176.0, date(2023, 1, 2): 178.0}
    assert "fechahasta=2022-12-31" in urls[0] and len(urls) == 3


def test_a_corrected_quote_is_logged_and_a_day_not_asked_for_stays(session):
    load_rates(session, {date(2023, 1, 2): 100.0, date(2023, 1, 3): 101.0}, "USD", 1, None)
    assert load_rates(session, {date(2023, 1, 3): 102.0, date(2023, 1, 4): 103.0}, "USD", 1, None) == 1
    session.commit()
    assert session.get(TipoCambioDiario, ("USD", date(2023, 1, 2))).valor == 100.0
    assert session.get(TipoCambioDiario, ("USD", date(2023, 1, 3))).valor == 102.0
    revision = session.scalars(select(DataRevision)).one()
    assert (revision.old_value, revision.new_value) == (101.0, 102.0)


def test_each_month_averages_its_quotes_and_the_latest_is_found(session):
    load_rates(session, {date(2023, 1, 2): 100.0, date(2023, 1, 3): 110.0, date(2023, 2, 1): 200.0}, "USD", 1, None)
    assert monthly_rates(session, "USD") == {"2023-01": 105.0, "2023-02": 200.0}
    assert latest_rate(session, "USD").fecha == date(2023, 2, 1)
    # always a day before today, even if today's quote is already stored
    assert latest_rate(session, "USD", today=date(2023, 2, 1)).fecha == date(2023, 1, 3)
    assert latest_rate(session, "USD", today=date(2023, 1, 2)) is None


def test_later_runs_only_ask_for_the_recent_days(session, monkeypatch):
    asked = []

    def fake(conf, start, end):
        asked.append(start)
        return {date(2023, 1, 20): 100.0}

    monkeypatch.setattr(bcra_fx, "fetch_rates", fake)
    assert run_bcra_source(session, "bcra_dolar", _run(session)) == (1, [])
    session.commit()
    run_bcra_source(session, "bcra_dolar", _run(session))
    options = sources().get("bcra_dolar").options
    assert asked[0] == date(options["first_year"], 1, 1)
    assert asked[1] == date(2023, 1, 20).fromordinal(date(2023, 1, 20).toordinal() - options["overlap_days"])
