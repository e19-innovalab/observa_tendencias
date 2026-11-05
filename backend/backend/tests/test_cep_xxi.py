from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.sector_kpis_run import cep_series
from app.core.config_files import analytics_params
from app.datasets import cep_xxi
from app.datasets.cep_xxi import (
    load_cep,
    macro_rows,
    read_series,
    run_cep_source,
    sector_activities,
    sector_years,
)
from app.datasets.ingest import DatasetError
from app.models import (
    Alert,
    Base,
    Country,
    DataRevision,
    DatasetFile,
    FactOcupacionTerciarios,
    FactoresMacroPPA,
    FactSalario,
    IngestionRun,
    Source,
    TipoCambioDiario,
)

CONF = analytics_params("cep_xxi")


def test_suppressed_cells_are_not_values():
    out = read_series(b"fecha,clae2,puestos\n2023-01-01,62,100\n2023-01-01,63,-99\n", "puestos", CONF)
    assert out == {("2023-01", 62): 100.0}


def test_a_file_without_its_columns_is_refused():
    with pytest.raises(ValueError):
        read_series(b"a,b\n1,2\n", "puestos", CONF)


def test_sectors_use_the_catalog_activities():
    activities = sector_activities()
    assert activities["Tecnología"] == {62, 63} and 86 in activities["Salud"] and 35 in activities["Energía"]


def test_jobs_average_the_months_and_wages_are_weighted_by_jobs():
    jobs = {("2022-01", 62): 100.0, ("2022-02", 62): 300.0, ("2022-01", 63): 100.0, ("2022-01", 1): 1000.0}
    wages = {("2022-01", 62): 10.0, ("2022-02", 62): 20.0, ("2022-01", 63): 40.0}
    women = {("2022-01", 62): 0.5}
    rows = {(r["sector"], r["anio"]): r for r in sector_years(jobs, wages, women, CONF)}
    tech = rows[("Tecnología", 2022)]
    assert tech["puestos"] == 250.0 and tech["meses"] == 2
    assert tech["salario"] == (10 * 100 + 20 * 300 + 40 * 100) / 500
    assert tech["pct_mujeres"] == 50.0
    assert rows[("Total", 2022)]["puestos"] == (1200 + 300) / 2


def test_a_factor_no_longer_published_follows_the_prices_of_both_countries():
    rows = macro_rows({("ARG", 2017): 10.0}, {}, {}, {2017: [100.0] * 12, 2018: [150.0] * 12, 2019: [300.0] * 12, 2020: [1.0]},
                      CONF, {2017: 100.0, 2018: 110.0, 2019: 121.0})
    found = {r["anio"]: r for r in rows if r["pais"] == "ARG"}
    assert found[2017]["metodo_ppa"] == CONF["ppp_method"]
    assert found[2018]["factor_ppa"] == pytest.approx(10 * 1.5 / 1.1)
    assert found[2019]["factor_ppa"] == pytest.approx(10 * 1.5 / 1.1 * 2 / 1.1)
    assert found[2019]["metodo_ppa"] == CONF["ppp_extended_method"]


def test_each_month_converts_at_its_rate_and_a_month_without_one_leaves_no_dollars():
    jobs = {("2022-01", 62): 100.0, ("2022-02", 62): 300.0, ("2022-01", 63): 100.0}
    wages = {("2022-01", 62): 10.0, ("2022-02", 62): 20.0, ("2022-01", 63): 40.0}
    rows = {(r["sector"], r["anio"]): r for r in sector_years(jobs, wages, {}, CONF, {"2022-01": 10.0, "2022-02": 20.0})}
    assert rows[("Tecnología", 2022)]["salario_usd"] == (10 * 100 / 10 + 20 * 300 / 20 + 40 * 100 / 10) / 500
    rows = {(r["sector"], r["anio"]): r for r in sector_years(jobs, wages, {}, CONF, {"2022-01": 10.0})}
    assert rows[("Tecnología", 2022)]["salario_usd"] is None


def test_argentine_prices_need_a_full_year_and_others_come_from_the_world_bank():
    rows = macro_rows({("ARG", 2017): 10.0}, {("CHL", 2016): 80.0, ("CHL", 2018): 100.0, ("ARG", 2017): 999.0},
                      {("ARG", 2017): 20.0}, {2017: [100.0] * 12, 2016: [100.0]}, CONF)
    found = {(r["pais"], r["anio"]): r for r in rows}
    assert found[("ARG", 2017)]["ipc_original"] == 100.0 and found[("ARG", 2017)]["factor_ppa"] == 10.0
    assert found[("ARG", 2017)]["tipo_cambio"] == 20.0 and found[("ARG", 2017)]["ipc_base_2016"] is None
    assert ("ARG", 2016) not in found and found[("CHL", 2018)]["ipc_base_2016"] == 125.0


@pytest.fixture
def session():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=[t.__table__ for t in (
        Country, Source, IngestionRun, DatasetFile, DataRevision, Alert, FactSalario, FactOcupacionTerciarios, FactoresMacroPPA,
        TipoCambioDiario)])
    with Session(engine) as s:
        s.add(Source(source_id=1, source_code="cep_xxi_argentina", name="C", source_kind="dataset"))
        s.commit()
        yield s


def _row(year, wage=100.0, jobs=10.0, months=12, usd=None):
    return {"sector": "Salud", "anio": year, "meses": months, "puestos": jobs, "salario": wage, "salario_usd": usd,
            "pct_mujeres": 60.0}


MACRO = [{"pais": "ARG", "anio": 2017, "ipc_original": 100.0, "factor_ppa": 10.0, "tipo_cambio": 50.0},
         {"pais": "ARG", "anio": 2018, "ipc_original": 200.0, "factor_ppa": 20.0, "tipo_cambio": 100.0},
         {"pais": "ARG", "anio": 2019, "ipc_original": 400.0, "factor_ppa": 40.0, "tipo_cambio": 200.0}]


def test_real_index_discounts_prices_and_other_sources_are_kept(session):
    session.add(FactSalario(pais="ARG", fuente_id="OIT_ILOSTAT", sector="Salud", anio=2017, sexo="T", salario_usd_ppa=5.0))
    load_cep(session, [_row(2017, 100.0), _row(2018, 300.0, usd=3.0)], MACRO, 1, None, CONF)
    session.commit()
    out = {i["anio"]: i for i in cep_series(session)["cep_xxi"]}
    assert out[2017]["indice_real"] == 100.0 and out[2018]["indice_real"] == 150.0
    assert out[2018]["salario_usd_ppa"] == 15.0 and out[2018]["salario_usd"] == 3.0
    assert len(session.scalars(select(FactSalario)).all()) == 3


def test_a_year_with_missing_months_keeps_pesos_and_dollars_and_gets_no_yearly_factor(session):
    load_cep(session, [_row(2017, 100.0), _row(2019, 800.0, months=11, usd=4.0)], MACRO, 1, None, CONF)
    session.commit()
    partial = {i["anio"]: i for i in cep_series(session)["cep_xxi"]}[2019]
    assert partial["salario_ars"] == 800.0 and partial["meses"] == 11
    assert partial["salario_usd"] == 4.0
    assert partial["salario_usd_ppa"] is None and partial["indice_real"] is None


def test_a_factor_a_source_stops_publishing_stays(session):
    load_cep(session, [_row(2017)], MACRO, 1, None, CONF)
    session.commit()
    load_cep(session, [_row(2017)], [{"pais": "ARG", "anio": 2017, "ipc_original": 100.0}], 1, None, CONF)
    session.commit()
    assert session.get(FactoresMacroPPA, ("ARG", 2018)).factor_ppa == 20.0
    assert session.get(FactoresMacroPPA, ("ARG", 2017)).factor_ppa == 10.0


def test_a_factor_from_a_retired_method_does_not_stay(session):
    session.add(FactoresMacroPPA(pais="ARG", anio=2025, factor_ppa=9.0, metodo_ppa="otro método"))
    session.flush()
    load_cep(session, [_row(2017)], MACRO, 1, None, CONF)
    session.commit()
    assert session.get(FactoresMacroPPA, ("ARG", 2025)).factor_ppa is None
    revision = session.scalars(select(DataRevision)).one()
    assert (revision.old_value, revision.change) == (9.0, "removed")


def test_changes_are_logged(session):
    load_cep(session, [_row(2017, 100.0), _row(2018, 300.0)], MACRO, 1, None, CONF)
    session.commit()
    assert load_cep(session, [_row(2017, 110.0)], MACRO, 1, None, CONF) == 3  # revised wage; wage and jobs removed
    session.commit()


def _offline(monkeypatch, tmp_path, files):
    monkeypatch.setattr(cep_xxi, "_links", lambda conf: [(n, f"https://cdn.produccion.gob.ar/{n}.csv") for n in files])
    monkeypatch.setattr(cep_xxi, "download_sync", lambda url, *a, **k: files[url.rsplit("/", 1)[1][:-4]])
    monkeypatch.setattr(cep_xxi, "_world_bank", lambda indicator, conf, countries=None: {("ARG", 2017): 10.0})
    monkeypatch.setattr(cep_xxi, "_indec_cpi", lambda conf: {2017: [100.0] * 12})
    conf = cep_xxi.app_config().datasets
    monkeypatch.setattr(type(conf), "path", lambda self, d: tmp_path)


GOOD = {"jobs": b"fecha,clae2,puestos\n2017-01-01,86,10\n", "mean_wage": b"fecha,clae2,w_mean\n2017-01-01,86,100\n",
        "women": b"fecha,clae2,share_mujer\n2017-01-01,86,.5\n"}


def _run(session):
    from datetime import UTC, datetime

    run = IngestionRun(source_id=1, started_at=datetime.now(UTC), status="running", triggered_by="test")
    session.add(run)
    session.flush()
    return run


def test_run_loads_then_skips_while_the_files_are_the_same(session, monkeypatch, tmp_path):
    _offline(monkeypatch, tmp_path, GOOD)
    assert run_cep_source(session, "cep_xxi_argentina", _run(session))[0] > 0
    session.commit()
    assert run_cep_source(session, "cep_xxi_argentina", _run(session)) == (0, [])
    session.commit()
    assert {d.status for d in session.scalars(select(DatasetFile)).all()} == {"loaded"}


def test_new_factors_reload_the_same_files_and_are_logged(session, monkeypatch, tmp_path):
    _offline(monkeypatch, tmp_path, GOOD)
    run_cep_source(session, "cep_xxi_argentina", _run(session))
    session.commit()
    monkeypatch.setattr(cep_xxi, "_world_bank", lambda indicator, conf, countries=None: {("ARG", 2017): 20.0})
    assert run_cep_source(session, "cep_xxi_argentina", _run(session))[0] > 0
    session.commit()
    salud = session.scalars(select(FactSalario).where(FactSalario.sector == "Salud")).one()
    assert salud.salario_usd_ppa is None  # January alone is not a full year
    assert session.get(FactoresMacroPPA, ("ARG", 2017)).factor_ppa == 20.0
    assert {r.dataset for r in session.scalars(select(DataRevision)).all()} == {"factores_macro_ppa"}
    assert len(session.scalars(select(DatasetFile)).all()) == 3


def test_new_quotes_reload_the_same_files(session, monkeypatch, tmp_path):
    _offline(monkeypatch, tmp_path, GOOD)
    run_cep_source(session, "cep_xxi_argentina", _run(session))
    session.commit()
    assert session.scalars(select(FactSalario).where(FactSalario.sector == "Salud")).one().salario_usd is None
    session.add(TipoCambioDiario(moneda="USD", fecha=date(2017, 1, 2), valor=20.0))
    session.commit()
    assert run_cep_source(session, "cep_xxi_argentina", _run(session))[0] > 0
    session.commit()
    assert session.scalars(select(FactSalario).where(FactSalario.sector == "Salud")).one().salario_usd == 5.0
    assert run_cep_source(session, "cep_xxi_argentina", _run(session)) == (0, [])
    assert cep_series(session)["dolar_oficial"]["valor"] == 20.0


def test_a_changed_format_loads_nothing_and_raises_an_alert(session, monkeypatch, tmp_path):
    _offline(monkeypatch, tmp_path, {**GOOD, "jobs": b"otra,cosa\n1,2\n"})
    with pytest.raises(DatasetError):
        run_cep_source(session, "cep_xxi_argentina", _run(session))
    session.commit()
    assert session.scalars(select(FactSalario)).first() is None
    assert session.scalars(select(Alert)).one().alert_type == "source_format_changed"
