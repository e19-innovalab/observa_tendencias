import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from app.connectors.ilostat import IlostatConnector
from app.connectors.world_bank import WorldBankConnector
from app.core.config_files import catalog, indicators, sources
from app.normalization.normalizer import normalize
from app.normalization.periods import period_label, shift_period, to_period_range

FIXTURES = Path(__file__).parent / "fixtures"
COUNTRIES = [c.iso3 for c in catalog().countries]


def _spec(code: str):
    ind = indicators().get(code)
    return ind, ind.series[0]


@pytest.mark.parametrize(
    ("period", "freq", "start", "end", "label"),
    [
        ("2024", "A", date(2024, 1, 1), date(2024, 12, 31), "2024"),
        ("2024-Q2", "Q", date(2024, 4, 1), date(2024, 6, 30), "2024-Q2"),
        ("2024Q4", "Q", date(2024, 10, 1), date(2024, 12, 31), "2024-Q4"),
        ("2024-02", "M", date(2024, 2, 1), date(2024, 2, 29), "2024-02"),
        ("2023M11", "M", date(2023, 11, 1), date(2023, 11, 30), "2023-11"),
    ],
)
def test_periods(period, freq, start, end, label):
    assert to_period_range(period, freq) == (start, end)
    assert period_label(start, freq) == label


def test_world_bank_to_canonical():
    body = json.loads((FIXTURES / "world_bank_SL.UEM.1524.ZS.json").read_text())
    ind, series = _spec("youth_unemployment_rate")
    conn = WorldBankConnector(sources().get("world_bank"), COUNTRIES)
    recs = conn.to_canonical({"indicator": ind, "series": series, "meta": body[0], "rows": body[1]})
    assert {r.country_iso3 for r in recs} == set(COUNTRIES)
    assert all(r.unit == ind.unit and r.source_updated_at == date(2026, 10, 8) for r in recs)


def test_ilostat_national_series():
    ind, series = _spec("unemployment_rate")
    conn = IlostatConnector(sources().get("ilostat"), COUNTRIES)
    text = (FIXTURES / "ilostat_DF_UNE_DEAP_SEX_AGE_RT.csv").read_text()
    recs = conn.to_canonical({"indicator": ind, "series": series, "csv": text})
    assert recs and all(r.sector_code is None for r in recs)


def test_ilostat_sector_mapping_and_aggregation():
    ind, series = _spec("employment")
    conn = IlostatConnector(sources().get("ilostat"), COUNTRIES)
    text = (FIXTURES / "ilostat_DF_EMP_TEMP_SEX_ECO_NB.csv").read_text()
    recs = conn.to_canonical({"indicator": ind, "series": series, "csv": text})
    by_key = {(r.country_iso3, r.period, r.sector_code): r.value for r in recs}
    # every catalog sector plus the national total, for one known year
    sectors = {r.sector_code for r in recs if r.country_iso3 == "CHL" and r.period == "2023"}
    assert sectors == {s.sector_code for s in catalog().sectors} | {None}
    # knowledge economy = J + M, technology = J  ->  knowledge economy > technology
    assert by_key[("CHL", "2023", "knowledge_economy")] > by_key[("CHL", "2023", "technology")]
    assert by_key[("CHL", "2023", None)] > by_key[("CHL", "2023", "knowledge_economy")]


def test_normalizer_reports_unmapped():
    from app.connectors.base import CanonicalRecord

    good = CanonicalRecord(indicator_code="gdp_growth", country_iso3="ARG", period="2024",
                           frequency="A", value=1.0, unit="percent")
    bad = good.model_copy(update={"country_iso3": "BRA"})
    res = normalize([good, bad], source_id=1, run_id=None, fetched_at=datetime.now(UTC))
    assert len(res.rows) == 1 and res.rows[0]["period_end"] == date(2024, 12, 31)
    assert res.issues == ["país fuera del catálogo BRA"]


def test_shift_period():
    assert shift_period(date(2024, 1, 1), "A", 2) == (date(2026, 1, 1), date(2026, 12, 31))
    assert shift_period(date(2024, 10, 1), "Q", 1) == (date(2025, 1, 1), date(2025, 3, 31))
    assert shift_period(date(2024, 12, 1), "M", 2) == (date(2025, 2, 1), date(2025, 2, 28))


def test_datos_argentina_quarterly_scale_and_labels():
    from app.connectors.datos_argentina import DatosArgentinaConnector

    body = json.loads((FIXTURES / "datos_argentina_42.3_EPH_PUNTUATAL_0_M_30.json").read_text())
    ind, series = _spec("unemployment_rate_quarterly")
    conn = DatosArgentinaConnector(sources().get("datos_argentina"), COUNTRIES)
    recs = conn.to_canonical({"indicator": ind, "series": series, "rows": body["data"]})
    by_period = {r.period: r.value for r in recs}
    assert by_period["2025-Q2"] == pytest.approx(7.576, abs=1e-3)  # fraction scaled to percent
    assert all(r.country_iso3 == "ARG" and r.frequency == "Q" for r in recs)


def test_pct_change_year_ago_matches_same_period():
    from app.connectors.datos_argentina import pct_change_year_ago

    rows = [(date(2023, 1, 1), 100.0), (date(2023, 2, 1), 110.0),
            (date(2024, 1, 1), 150.0), (date(2024, 3, 1), 200.0)]
    # Feb-2024 missing and Mar-2023 missing: only Jan-2024 has a base
    assert pct_change_year_ago(rows) == [(date(2024, 1, 1), pytest.approx(0.5))]


def test_datos_argentina_merges_stale_reads(monkeypatch):
    """Stale cached answers return null for periods with data; reads are merged."""
    import asyncio

    from app.connectors.datos_argentina import DatosArgentinaConnector

    reads = iter([
        [["2025-01-01", 0.079], ["2025-04-01", None], ["2025-07-01", None]],
        [["2025-01-01", None], ["2025-04-01", 0.0757], ["2025-07-01", None]],
    ] + [[["2025-07-01", 0.066]]] * 10)
    limits = []

    async def fake_read(self, client, params):
        limits.append(params["limit"])
        return next(reads)

    monkeypatch.setattr(DatosArgentinaConnector, "_read", fake_read)
    conn = DatosArgentinaConnector(sources().get("datos_argentina"), COUNTRIES)
    payload = asyncio.run(conn.fetch([_spec("unemployment_rate_quarterly")], None))[0]
    assert payload["rows"] == [["2025-01-01", 0.079], ["2025-04-01", 0.0757],
                               ["2025-07-01", 0.066]]
    assert len(set(limits)) == len(limits)  # every read hits a different cache entry


def test_ilostat_occupation_groups_shared_by_catalog_occupations():
    ind = indicators().get("employment")
    series = next(s for s in ind.series if s.occupation_dimension)
    conn = IlostatConnector(sources().get("ilostat"), COUNTRIES)
    text = (FIXTURES / "ilostat_DF_EMP_TEMP_SEX_OC2_NB.csv").read_text()
    recs = conn.to_canonical({"indicator": ind, "series": series, "csv": text})
    by = {(r.country_iso3, r.period, r.occupation_code): r.value for r in recs}
    # ISCO 25xx: systems analyst, software, web and network share the 2-digit group value
    it = {by[("ARG", "2024", o)] for o in ("2511", "2512", "2513", "2523")}
    assert len(it) == 1
    assert all(r.sector_code is None for r in recs)
    universe = {o.occupation_code for o in catalog().occupations}
    assert {r.occupation_code for r in recs} <= universe
    assert {o.occupation_code for o in catalog().occupations if o.is_featured} <= {
        r.occupation_code for r in recs}


def test_reference_table_values_for_every_country():
    import asyncio

    from app.connectors.reference_table import ReferenceTableConnector

    ind = indicators().get("genai_exposure")
    conn = ReferenceTableConnector(sources().get("ilo_genai_exposure"), COUNTRIES)
    payload = asyncio.run(conn.fetch([(ind, ind.series[0])], None))[0]
    recs = conn.to_canonical(payload)
    assert len(recs) == 427 * len(COUNTRIES)  # every row of ILO Table A1
    cook = [r for r in recs if r.occupation_code == "5120"]
    assert {r.value for r in cook} == {0.18} and {r.country_iso3 for r in cook} == set(COUNTRIES)
    assert cook[0].source_updated_at == date(2025, 5, 1) and cook[0].period == "2025"


def test_simel_annual_mean_of_calendar_quarters_and_quality_flags():
    from statistics import fmean

    from app.connectors.simel import SimelConnector

    ind = indicators().get("employment")
    series = next(s for s in ind.series if s.source == "simel_chile")
    conn = SimelConnector(sources().get("simel_chile"), COUNTRIES)
    text = (FIXTURES / "simel_DF_OCUCIUO_CIUO_SEXO.csv").read_text()
    recs = conn.to_canonical({"indicator": ind, "series": series, "csv": text})
    assert {r.period for r in recs} == {"2024", "2025"}  # 2026 is incomplete
    assert {r.country_iso3 for r in recs} == {"CHL"}
    # group 2 (professionals) feeds every 2xxx occupation; mean of JFM, AMJ, JAS, OND, in thousands
    rows = [ln.split(",") for ln in text.splitlines()[1:]]
    q = {r[6][:7]: float(r[7]) for r in rows if r[4] == "CIUO_2" and r[6].startswith("2025")}
    expected = fmean(q[m] for m in ("2025-01", "2025-04", "2025-07", "2025-10")) / 1000
    dev = next(r for r in recs if r.occupation_code == "2512" and r.period == "2025")
    assert dev.value == pytest.approx(expected)
    # group 0 ("no identificado") is not an ISCO group of the catalog and its estimates are
    # flagged unreliable: nothing is produced for it
    assert not any(r.occupation_code and r.occupation_code.startswith("0") for r in recs)


def test_series_country_restriction():
    ilo = next(s for s in indicators().get("employment").series if s.occupation_dimension == "OC2")
    simel = next(s for s in indicators().get("employment").series if s.source == "simel_chile")
    assert ilo.countries == ["ARG", "URY"] and simel.countries == ["CHL"]
    conn = IlostatConnector(sources().get("ilostat"), COUNTRIES)
    text = (FIXTURES / "ilostat_DF_EMP_TEMP_SEX_OC2_NB.csv").read_text()
    chl_row = text.splitlines()[1].replace(",ARG,", ",CHL,", 1)
    recs = conn.to_canonical({"indicator": indicators().get("employment"), "series": ilo,
                              "csv": text + "\n" + chl_row})
    assert "CHL" not in {r.country_iso3 for r in recs}


def _mismatch_csv(rows: list[tuple]) -> str:
    lines = ["REF_AREA,FREQ,MEASURE,SEX,OCU,EDU,TIME_PERIOD,OBS_VALUE,OBS_STATUS"]
    lines += [f"{c},A,EMP_TEMP_NB,SEX_T,{o},{e},{y},{v},{s}" for c, o, e, y, v, s in rows]
    return "\n".join(lines)


def test_ilostat_education_mismatch_bands_breaks_and_impossible_groups():
    conn = IlostatConnector(sources().get("ilostat"), COUNTRIES)
    text = _mismatch_csv([
        # 2024, ARG: clerks (group 4, require secondary) and professionals (group 2, tertiary)
        ("ARG", "OCU_ISCO08_4", "EDU_ISCED97_5", "2024", 30, ""),  # over
        ("ARG", "OCU_ISCO08_4", "EDU_ISCED97_3", "2024", 60, ""),  # matched
        ("ARG", "OCU_ISCO08_4", "EDU_ISCED97_1", "2024", 10, ""),  # under
        ("ARG", "OCU_ISCO08_2", "EDU_ISCED97_5", "2024", 80, ""),
        ("ARG", "OCU_ISCO08_2", "EDU_ISCED97_3", "2024", 20, ""),  # under
        # left out: totals, armed forces, education not stated
        ("ARG", "OCU_ISCO08_TOTAL", "EDU_ISCED97_3", "2024", 999, ""),
        ("ARG", "OCU_ISCO08_0", "EDU_ISCED97_3", "2024", 999, ""),
        ("ARG", "OCU_ISCO08_4", "EDU_ISCED97_UNK", "2024", 999, ""),
        ("ARG", "OCU_ISCO08_4", "EDU_AGGREGATE_INT", "2024", 999, ""),
        # URY: break in 2022, so 2019 is dropped
        ("URY", "OCU_ISCO08_4", "EDU_ISCED97_1", "2019", 50, ""),
        ("URY", "OCU_ISCO08_4", "EDU_ISCED97_3", "2022", 50, "B"),
        ("URY", "OCU_ISCO08_4", "EDU_ISCED97_0", "2022", 50, ""),
    ])
    out = {}
    for code in ("overeducation_rate", "undereducation_rate"):
        ind, series = _spec(code)
        out[code] = {(r.country_iso3, r.period, r.occupation_code): r.value
                     for r in conn.to_canonical({"indicator": ind, "series": series, "csv": text})}
    over, under = out["overeducation_rate"], out["undereducation_rate"]
    assert over[("ARG", "2024", None)] == pytest.approx(15.0)  # 30 of 200
    assert under[("ARG", "2024", None)] == pytest.approx(15.0)  # (10 + 20) of 200
    assert over[("ARG", "2024", "4110")] == pytest.approx(30.0)
    assert under[("ARG", "2024", "2511")] == pytest.approx(20.0)
    # professionals cannot be over-qualified: no 0 % stored for them
    assert ("ARG", "2024", "2511") not in over
    assert under[("URY", "2022", None)] == pytest.approx(50.0)  # pre-primary counts as primary
    assert not any(k[0] == "URY" and k[1] == "2019" for k in under)
