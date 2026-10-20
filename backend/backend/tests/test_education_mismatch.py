from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.connectors.ilostat import IlostatConnector
from app.core.config_files import app_config, catalog, indicators, sources
from app.core.database import get_session
from app.ingestion.pipeline import replace_education_cells
from app.main import app
from app.models import Base, Country, IngestionRun, Source
from tests.conftest import sqlite_tables
from tests.test_connectors import _mismatch_csv

ROWS = [
    ("ARG", "OCU_ISCO08_4", "EDU_ISCED97_5", "2024", 30, ""),  # over
    ("ARG", "OCU_ISCO08_4", "EDU_ISCED97_3", "2024", 60, ""),  # matched
    ("ARG", "OCU_ISCO08_4", "EDU_ISCED97_1", "2024", 10, ""),  # under
    ("ARG", "OCU_ISCO08_4", "EDU_ISCED97_UNK", "2024", 5, ""),  # not stated: shown, not counted
    ("ARG", "OCU_ISCO08_2", "EDU_ISCED97_5", "2024", 80, ""),
    ("ARG", "OCU_ISCO08_2", "EDU_ISCED97_3", "2024", 20, ""),  # under
    ("ARG", "OCU_ISCO08_0", "EDU_ISCED97_3", "2024", 7, ""),  # armed forces: shown, not counted
    ("ARG", "OCU_ISCO08_TOTAL", "EDU_ISCED97_3", "2024", 999, ""),  # totals are not cells
    ("ARG", "OCU_ISCO08_4", "EDU_ISCED97_3", "2023", 100, ""),
]


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=sqlite_tables())
    countries = [c.iso3 for c in catalog().countries]
    conn = IlostatConnector(sources().get("ilostat"), countries)
    ind = indicators().get("overeducation_rate")
    payload = {"indicator": ind, "series": ind.series[0], "csv": _mismatch_csv(ROWS)}
    with Session(engine) as s:
        s.add_all([Country(iso3=c, name_es=c, name_en=c) for c in countries])
        s.add(Source(source_id=1, source_code="ilostat", name="ILOSTAT", source_kind="api",
                     expected_frequency="weekly"))
        s.add(IngestionRun(run_id=1, source_id=1, started_at=datetime.now(UTC), status="success",
                           triggered_by="manual"))
        # two payloads with the same table (over and under series): stored once
        replace_education_cells(s, 1, 1, conn.education_cells(payload) * 2)
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_cells_reproduce_the_rates(client):
    d = client.get("/api/v1/education-mismatch", params={"country": "arg"}).json()
    assert d["year"] == 2024 and d["years"] == [2023, 2024]
    assert d["totals"] == {"matched": 140.0, "over": 30.0, "under": 30.0, "considered": 200.0,
                           "excluded": 12.0}
    # the same numbers as the stored indicators (see test_connectors)
    assert d["over_rate"] == pytest.approx(0.15) and d["under_rate"] == pytest.approx(0.15)
    assert d["indicators"] == {"over": "overeducation_rate", "under": "undereducation_rate"}
    groups = {g["isco_group"]: g for g in d["groups"]}
    assert list(groups) == ["2", "4", "0"]  # requirement order, excluded groups last
    clerks = groups["4"]
    assert clerks["required_band"] == "secondary" and clerks["total"] == 105.0
    assert clerks["over_share"] == pytest.approx(0.3) and clerks["under_share"] == pytest.approx(0.1)
    assert {c["band"]: c["status"] for c in clerks["cells"]}["not_stated"] == "excluded"
    assert groups["2"]["over_share"] is None  # professionals cannot be over-qualified
    assert groups["0"]["required_band"] is None and groups["0"]["excluded_reason"]
    assert d["explanation"] and d["bands"][-1]["code"] == "not_stated"
    assert d["page_size"] == app_config().pagination.ranking_size
    assert [s["status"] for s in d["statuses"]] == ["matched", "over", "under", "excluded"]


def test_year_and_country_without_data(client):
    assert client.get("/api/v1/education-mismatch",
                      params={"country": "ARG", "year": 2023}).json()["totals"]["considered"] == 100
    assert client.get("/api/v1/education-mismatch", params={"country": "URY"}).status_code == 404
    assert client.get("/api/v1/education-mismatch",
                      params={"country": "ARG", "year": 1990}).status_code == 404
