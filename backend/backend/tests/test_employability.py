from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.employability_run import Point, dimension_value
from app.analytics.recompute import recompute
from app.core.config_files import analytics_params, catalog
from app.core.database import get_session
from app.ingestion.pipeline import upsert_observations
from app.main import app
from app.models import (
    Base,
    Country,
    Methodology,
    Source,
)
from tests.conftest import sqlite_tables

FETCHED = datetime(2026, 10, 17, tzinfo=UTC)
DIMS = analytics_params("employability")["dimensions"]


def test_growth_skips_excluded_years_and_small_bases():
    conf = DIMS["net_demand"]
    pts = [Point(2020, 70, "ilostat", None), Point(2022, 129, "ilostat", None)]
    assert dimension_value(pts, conf, 2025, 5) == (None, {})  # only 2022 left after exclusion
    pts = [Point(2022, 100, "ilostat", None), Point(2025, 133.1, "ilostat", None)]
    growth, detail = dimension_value(pts, conf, 2025, 5)
    assert growth == pytest.approx(0.1) and detail["from_period"] == "2022"
    small = [Point(2022, 6.6, "ilostat", None), Point(2025, 9.1, "ilostat", None)]
    assert dimension_value(small, conf, 2025, 5)[0] is None  # below min_base


def test_reference_dimension_applies_to_every_year():
    pts = [Point(2025, 0.5, "ilo_genai_exposure", date(2025, 5, 1))]
    assert dimension_value(pts, DIMS["automation_risk"], 2018, 5)[0] == 0.5
    assert dimension_value(pts, DIMS["salary_ppp"], 2018, 5)[0] is None  # yearly data: no


def _obs(source_id, indicator, country, occupation, year, value, unit):
    return dict(indicator_code=indicator, country_iso3=country, sector_code=None,
                occupation_code=occupation, period_start=date(year, 1, 1),
                period_end=date(year, 12, 31), frequency="A", value=value, unit=unit,
                data_type="observed", source_id=source_id, run_id=None,
                source_updated_at=None, fetched_at=FETCHED)


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=sqlite_tables())
    occs = ["2512", "2221", "5120"]
    with Session(engine) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en)
                   for c in catalog().countries])
        s.add_all([Source(source_id=1, source_code="ilostat", name="ILOSTAT", source_kind="api"),
                   Source(source_id=2, source_code="ilo_genai_exposure", name="OIT",
                          source_kind="dataset")])
        rows = []
        growth = {"2512": 1.10, "2221": 1.00, "5120": 1.02}
        salary = {"2512": 2500, "2221": 2000, "5120": 1200}
        risk = {"2512": 0.53, "2221": 0.25, "5120": 0.18}
        for occ in occs:
            for i, year in enumerate(range(2022, 2026)):
                rows.append(_obs(1, "employment", "ARG", occ, year, 100 * growth[occ] ** i,
                                 "thousands_persons"))
            rows.append(_obs(1, "mean_monthly_earnings_ppp", "ARG", occ, 2025, salary[occ],
                             "ppp_usd_month"))
            rows.append(_obs(2, "genai_exposure", "ARG", occ, 2025, risk[occ], "index_0_1"))
        # salary in USD (shown, not scored): only 2512, and one year that the index did not use
        rows.append(_obs(1, "mean_monthly_earnings_usd", "ARG", "2512", 2025, 1300, "usd_month"))
        rows.append(_obs(1, "mean_monthly_earnings_usd", "ARG", "2221", 2024, 900, "usd_month"))
        upsert_observations(s, rows)
        s.commit()
        recompute(s)
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app), engine
    app.dependency_overrides.clear()


def test_scores_rank_and_trace_components(client):
    c, _ = client
    r = c.get("/api/v1/employability", params={"country": "ARG"}).json()
    assert r["year"] == 2025 and 2025 in r["available_years"]
    scored = [i for i in r["items"] if i["score"] is not None]
    # nurse: (0·.35 + 61.54·.25 + 80·.15)/.75 = 36.51 · cook: (20·.35 + 0·.25 + 100·.15)/.75 = 29.3
    assert [i["occupation"]["occupation_code"] for i in scored] == [
        "2512", "2221", "5120"]
    by = {i["occupation"]["occupation_code"]: i["score"] for i in scored}
    assert by["2221"] == pytest.approx(36.51, abs=0.01)
    assert by["5120"] == pytest.approx(29.33, abs=0.01)
    top = scored[0]
    assert top["coverage_ratio"] == pytest.approx(0.75) and top["data_type"] == "calculated"
    comps = {x["dimension"]: x for x in top["components"]}
    assert comps["insertion_rate"]["available"] is False
    assert sum(x["contribution"] or 0 for x in top["components"]) == pytest.approx(top["score"])
    assert comps["net_demand"]["detail"]["from_period"] == "2022"
    assert comps["net_demand"]["raw"] == pytest.approx(0.10)


def test_occupations_without_data_are_insufficient(client):
    c, _ = client
    r = c.get("/api/v1/employability", params={"country": "URY", "view": "all"}).json()
    assert r["items"] and all(i["level"] in ("insufficient_data", "not_applicable")
                              for i in r["items"])
    assert c.get("/api/v1/employability", params={"country": "URY"}).json()["items"] == []


def test_history_and_profile(client):
    c, engine = client
    hist = c.get("/api/v1/employability/history",
                 params={"occupation": "2221", "country": "ARG"}).json()[0]
    assert [p["year"] for p in hist["points"]][-1] == 2025
    prof = c.get("/api/v1/occupations/2512").json()
    groups = {(g["indicator"], g["source"]): g for g in prof["groups"]}
    assert groups[("employment", "simel_chile")]["group_code"] == "CIUO_2"
    assert groups[("employment", "simel_chile")]["countries"] == ["CHL"]
    groups = {g["indicator"]: g for g in prof["groups"] if g["source"] == "ilostat"}
    assert groups["employment"]["group_code"] == "OC2_ISCO08_25"
    assert groups["employment"]["countries"] == ["ARG", "URY"]
    # every other 25xx unit group shares the 2-digit employment figure
    assert {"2511", "2513", "2514", "2519", "2521", "2522", "2523", "2529"} <= set(
        groups["employment"]["shared_with"])
    assert {e["country_iso3"] for e in prof["employability"]} == {"ARG", "URY", "CHL"}
    assert prof["occupation"]["is_featured"] and prof["sector_name"] == "Tecnología"
    assert c.get("/api/v1/occupations/nope").status_code == 404
    with Session(engine) as s:  # every score points to the employability methodology
        m = s.scalar(select(Methodology).where(Methodology.methodology_type == "employability_index"))
        assert m.params["weights"]["net_demand"] == 0.35


def test_views_top_bottom_and_all(client):
    c, _ = client
    top = c.get("/api/v1/employability", params={"view": "top", "limit": 2}).json()
    bottom = c.get("/api/v1/employability", params={"view": "bottom", "limit": 2}).json()
    full = c.get("/api/v1/employability", params={"view": "all", "limit": 500}).json()
    assert [i["occupation"]["occupation_code"] for i in top["items"]] == ["2512", "2221"]
    assert [i["occupation"]["occupation_code"] for i in bottom["items"]] == ["5120", "2221"]
    assert top["scored_total"] == 3 and full["total"] == 436 * 3
    assert [i["score"] is None for i in full["items"]][:3] == [False] * 3
    assert all(i["score"] is None for i in full["items"][3:])
    page = c.get("/api/v1/employability", params={"view": "all", "limit": 2, "offset": 1}).json()
    assert [i["occupation"]["occupation_code"] for i in page["items"]] == ["2221", "5120"]


def test_filters_featured_and_search(client):
    c, _ = client
    r = c.get("/api/v1/employability", params={"view": "all", "featured": "true",
                                               "country": "ARG"}).json()
    assert r["total"] == 20
    r = c.get("/api/v1/employability", params={"view": "all", "q": "desarroll",
                                               "country": "ARG"}).json()
    assert "2512" in {i["occupation"]["occupation_code"] for i in r["items"]}


def test_sort_by_each_dimension(client):
    c, _ = client

    def codes(**params):
        r = c.get("/api/v1/employability", params={"country": "ARG", **params}).json()
        return [i["occupation"]["occupation_code"] for i in r["items"]], r

    # salary: 2512 = 2500, 2221 = 2000, 5120 = 1200
    assert codes(sort_by="salary_ppp", order="desc")[0] == ["2512", "2221", "5120"]
    assert codes(sort_by="salary_ppp", order="asc")[0] == ["5120", "2221", "2512"]
    # automation risk: 5120 = 0.18 (lowest) ... 2512 = 0.53
    assert codes(sort_by="automation_risk", order="asc")[0] == ["5120", "2221", "2512"]
    # net demand: 2512 +10%, 5120 +2%, 2221 0%
    got, r = codes(sort_by="net_demand")
    assert got == ["2512", "5120", "2221"] and r["order"] == "desc"
    # no data for insertion rate: nothing to rank; in "all" every row comes back
    assert codes(sort_by="insertion_rate")[0] == []
    assert len(codes(sort_by="insertion_rate", view="all", limit=500)[0]) == 436


def test_bottom_defaults_to_ascending_and_invalid_sort(client):
    c, _ = client
    r = c.get("/api/v1/employability", params={"view": "bottom", "sort_by": "salary_ppp"}).json()
    assert r["order"] == "asc" and r["items"][0]["occupation"]["occupation_code"] == "5120"
    bad = c.get("/api/v1/employability", params={"sort_by": "nope"})
    assert bad.status_code == 422 and "net_demand" in bad.json()["detail"]


def test_sort_by_name_code_and_country(client):
    c, _ = client

    def page(**params):
        return c.get("/api/v1/employability", params={"view": "all", "limit": 500, **params}).json()

    r = page(sort_by="occupation", country="ARG")
    names = [i["occupation"]["name"] for i in r["items"]]
    assert r["order"] == "asc" and names[0] < names[-1]
    # accents ignored: an occupation starting with "Ó" sorts among the O's, not after Z
    first_letters = [n[0].upper() for n in names]
    assert "Ó" not in first_letters[-5:]
    r = page(sort_by="isco", country="ARG")
    codes = [i["occupation"]["occupation_code"] for i in r["items"]]
    assert codes == sorted(codes)
    r = page(sort_by="isco", order="desc", country="ARG")
    assert r["items"][0]["occupation"]["occupation_code"] == max(codes)
    r = page(sort_by="country")
    assert [i["country_iso3"] for i in r["items"]][:1] == ["ARG"]
    # top/bottom by name list only scored occupations
    top = c.get("/api/v1/employability", params={"sort_by": "occupation"}).json()
    assert {i["occupation"]["occupation_code"] for i in top["items"]} == {"2512", "2221", "5120"}


def test_dimension_ranges_and_coverage_sort(client):
    c, _ = client
    r = c.get("/api/v1/employability", params={"country": "ARG"}).json()
    ranges = {d["dimension"]: d for d in r["dimension_ranges"]}
    assert ranges["salary_ppp"]["observed_min"] == 1200 and ranges["salary_ppp"]["observed_max"] == 2500
    assert ranges["automation_risk"]["higher_is_better"] is False
    assert ranges["insertion_rate"]["observed_min"] is None and ranges["insertion_rate"]["with_data"] == 0
    assert all(d["definition"] and d["possible_range"] for d in r["dimension_ranges"])
    # a dimension without a source: its weight goes to the others, and the API says so
    assert ranges["insertion_rate"]["has_source"] is False and ranges["insertion_rate"]["source_status"]
    assert ranges["insertion_rate"]["effective_weight"] == 0
    assert sum(d["effective_weight"] for d in r["dimension_ranges"]) == pytest.approx(1)
    assert ranges["net_demand"]["effective_weight"] == pytest.approx(0.35 / 0.75)
    assert "Tasa de inserción" in r["no_source_note"] and "46,7 %" in r["no_source_note"]
    # ranges describe the whole cohort (occupations that apply to the region), not the page
    from app.core.config_files import catalog

    applicable = sum(not o.is_excluded for o in catalog().occupations)
    assert ranges["salary_ppp"]["total"] == applicable * 3
    low = c.get("/api/v1/employability", params={"view": "all", "sort_by": "coverage",
                                                 "order": "asc", "limit": 1}).json()
    high = c.get("/api/v1/employability", params={"sort_by": "coverage", "limit": 1}).json()
    assert low["items"][0]["coverage_ratio"] <= high["items"][0]["coverage_ratio"] == 0.75


def test_excluded_occupations_stay_out_of_cohort_and_rankings(client):
    c, _ = client
    from app.core.config_files import catalog

    excluded = {o.occupation_code for o in catalog().occupations if o.is_excluded}
    assert {"1113", "6310", "6340"} <= excluded
    full = c.get("/api/v1/employability", params={"view": "all", "limit": 500, "q": "6310"}).json()
    rows = [i for i in full["items"] if i["occupation"]["occupation_code"] == "6310"]
    assert rows and all(i["level"] == "not_applicable" and i["score"] is None for i in rows)
    assert rows[0]["level_label"] == "No aplica a la región"
    assert rows[0]["occupation"]["is_excluded"] and rows[0]["occupation"]["exclusion_reason"]
    for view in ("top", "bottom"):
        r = c.get("/api/v1/employability", params={"view": view, "sort_by": "salary_ppp",
                                                   "limit": 500}).json()
        assert not {i["occupation"]["occupation_code"] for i in r["items"]} & excluded


def test_rankings_cap_occupations_per_isco_group(client, monkeypatch):
    c, _ = client
    from app.core.config_files import app_config

    # the three scored occupations are in groups 25, 22 and 51
    monkeypatch.setattr(app_config().employability.ranking, "max_per_group", 1)
    monkeypatch.setattr(app_config().employability.ranking, "group_digits", 1)
    r = c.get("/api/v1/employability", params={"view": "top", "country": "ARG"}).json()
    codes = [i["occupation"]["occupation_code"] for i in r["items"]]
    assert codes == ["2512", "5120"]  # 2221 (also group 2) is left out
    assert r["items"][0]["group_code"] == "2" and r["items"][0]["group_hidden"] == 1
    assert r["items"][1]["group_hidden"] == 0
    # the full list is never capped
    full = c.get("/api/v1/employability", params={"view": "all", "country": "ARG",
                                                  "limit": 500}).json()
    assert {"2512", "2221", "5120"} <= {i["occupation"]["occupation_code"] for i in full["items"]}


def test_sector_summary_averages_its_occupations(client):
    c, _ = client
    page = c.get("/api/v1/employability", params={"country": "ARG", "view": "all", "limit": 500}).json()
    score = {i["occupation"]["occupation_code"]: i["score"] for i in page["items"] if i["score"] is not None}
    r = c.get("/api/v1/employability/sectors", params={"country": "ARG"}).json()
    sectors = {s["sector_code"]: s for s in r["items"]}
    assert [s["sector_code"] for s in r["items"]] == [s.sector_code for s in catalog().sectors]
    tech = sectors["technology"]
    # only 2512 has data in technology: the sector average is its score
    assert tech["scored"] == 1 and tech["average_score"] == pytest.approx(score["2512"])
    assert tech["top_occupation"]["occupation_code"] == "2512"
    assert tech["salary_ppp_average"] == 2500 and tech["automation_average"] == pytest.approx(0.53)
    assert tech["level_label"] and set(tech["dimensions"]) == set(analytics_params("employability")["weights"])
    assert sectors["health"]["top_occupation"]["occupation_code"] == "2221"
    assert sectors["energy"]["average_score"] is None and sectors["energy"]["top_occupation"] is None
    scored = [score[o] for o in ("2512", "2221", "5120") if o in score]
    assert r["regional_average"] == pytest.approx(sum(scored) / len(scored))
    assert r["no_source_note"]  # insertion rate has no source yet


def test_salary_shown_in_usd_for_the_same_period(client):
    c, _ = client
    comps = {e["occupation"]["occupation_code"]: {x["dimension"]: x for x in e["components"]}
             for e in c.get("/api/v1/employability", params={"country": "ARG", "view": "all"}).json()["items"]}
    usd = comps["2512"]["salary_ppp"]["display"]
    assert usd["value"] == 1300 and usd["period"] == "2025" and usd["unit"] == "usd_month" and usd["note"]
    assert comps["2512"]["salary_ppp"]["raw"] == 2500  # the index still uses PPP
    assert comps["2221"]["salary_ppp"]["display"] is None  # USD only for another year
    assert comps["2512"]["net_demand"]["display"] is None
    profile = c.get("/api/v1/occupations/2512").json()
    assert any(x["display"] and x["display"]["value"] == 1300 for x in profile["employability"][0]["components"])
    sectors = {s["sector_code"]: s for s in c.get("/api/v1/employability/sectors", params={"country": "ARG"}).json()["items"]}
    assert sectors["technology"]["salary_usd_average"] == 1300 and sectors["health"]["salary_usd_average"] is None
    # the wording comes from app.yaml (employability), not from the frontend
    texts = profile["texts"]
    assert texts["terms"]["normalized"] and texts["terms"]["contribution"]
    assert "{value}" in texts["unit_formats"]["usd_month"] and texts["display"]["salary_ppp"]["note"]
    assert c.get("/api/v1/employability/sectors").json()["texts"] == texts
