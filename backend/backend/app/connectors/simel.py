"""SIMEL, Sistema de Información del Mercado Laboral (INE Chile). SDMX REST API (CSV).

GET {base_url}/data/{agency},{dataflow},{version}/{key}?startPeriod=
Periods are rolling quarters ("2026-04-01/P3M" = April-June). Observations flagged as unreliable
(exclude_status) are dropped. With `annualize`, a yearly value is the mean of the rolling
quarters starting in the configured months, for complete years only.
"""
import csv
import io
from collections import defaultdict
from statistics import fmean

from app.connectors.base import BaseConnector, CanonicalRecord, SeriesSpec
from app.connectors.http import get_with_retry, make_client
from app.connectors.ilostat import _occupations_by_code

PERIOD_COLUMN, VALUE_COLUMN, STATUS_COLUMN = "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS"


def _start(period: str) -> tuple[int, int]:
    """'2026-04-01/P3M' -> (2026, 4)."""
    year, month = period.split("/")[0].split("-")[:2]
    return int(year), int(month)


class SimelConnector(BaseConnector):
    async def fetch(self, specs: list[SeriesSpec], since_year: int | None) -> list[dict]:
        o = self.options
        payloads = []
        async with make_client() as client:
            for indicator, series in specs:
                url = (f"{self.source.base_url}/data/{o['agency']},{series.dataflow},"
                       f"{o['dataflow_version']}/{series.key}")
                start = f"{since_year}-01" if since_year else o["start_period"]
                response = await get_with_retry(client, url, params={"startPeriod": start},
                                                headers={"Accept": o["accept"]})
                payloads.append({"indicator": indicator, "series": series, "csv": response.text})
        return payloads

    def to_canonical(self, raw_payload: dict) -> list[CanonicalRecord]:
        indicator, series = raw_payload["indicator"], raw_payload["series"]
        excluded = set(self.options.get("exclude_status", []))
        rows = [r for r in csv.DictReader(io.StringIO(raw_payload["csv"]))
                if r.get(VALUE_COLUMN) not in (None, "") and r.get(STATUS_COLUMN) not in excluded]
        groups = _occupations_by_code(series.occupation_code_prefix, series.occupation_isco_digits) \
            if series.occupation_dimension else {}
        # (occupation group code or None, year) -> {start month: value}
        by_year: dict[tuple, dict[int, float]] = defaultdict(dict)
        for r in rows:
            code = r[series.occupation_dimension] if series.occupation_dimension else None
            if series.occupation_dimension and code not in groups:
                continue
            year, month = _start(r[PERIOD_COLUMN])
            by_year[(code, year)][month] = float(r[VALUE_COLUMN]) * series.scale

        months = (series.annualize or {}).get("months", [])
        records = []
        for (code, year), values in sorted(by_year.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
            if not months or not all(m in values for m in months):
                continue  # incomplete year
            value = fmean(values[m] for m in months)
            for occupation in groups.get(code, [None]) if code else [None]:
                records.append(CanonicalRecord(
                    indicator_code=indicator.code, country_iso3=self.options["country"],
                    occupation_code=occupation, period=str(year), frequency=series.frequency,
                    value=value, unit=indicator.unit,
                ))
        return records
