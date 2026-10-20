"""Datos Argentina, Series de Tiempo API (REST JSON, no authentication).

GET {base_url}/series/?ids={id}&start_date=&limit=&start=[&collapse=&collapse_aggregation=]
Response: {"data": [[date, value], ...], "count": n, "meta": [...]}.

One request per series: asking for several ids at once collapses them to the lowest common
frequency. The API caches each exact URL and some cached answers are stale (periods with data
come back null), so each series is read `reads` times with a different page size, which hits a
different cache entry each time, and non-null values are merged.

Year-over-year changes are computed here (not with the API's representation_mode) so the
formula is explicit and testable, and so the merge above works on the original levels.
"""
from datetime import date

from app.connectors.base import BaseConnector, CanonicalRecord, SeriesSpec
from app.connectors.http import get_with_retry, make_client
from app.normalization.periods import period_label


def _year_ago(d: date) -> date:
    return d.replace(year=d.year - 1)


def pct_change_year_ago(rows: list[tuple[date, float]]) -> list[tuple[date, float]]:
    """value / value at the same period one year earlier - 1; periods without a base are dropped."""
    by_date = dict(rows)
    out = []
    for d, v in rows:
        base = by_date.get(_year_ago(d))
        if base:
            out.append((d, v / base - 1))
    return out


class DatosArgentinaConnector(BaseConnector):
    async def fetch(self, specs: list[SeriesSpec], since_year: int | None) -> list[dict]:
        o = self.options
        start = date.fromisoformat(o["start_date"])
        if since_year:
            start = date(since_year, 1, 1)
        payloads = []
        async with make_client() as client:
            for indicator, series in specs:
                # a year-over-year change needs the year before the first reported period
                first = _year_ago(start) if series.transform else start
                params = {"ids": series.id, "start_date": first.isoformat()}
                if series.collapse:
                    params |= {"collapse": series.collapse,
                               "collapse_aggregation": series.collapse_aggregation}
                merged: dict[str, float | None] = {}
                for attempt in range(o["reads"]):
                    for d, v in await self._read(client, params | {"limit": o["page_size"] - attempt}):
                        if merged.get(d) is None:
                            merged[d] = v
                rows = sorted([d, v] for d, v in merged.items())
                payloads.append({"indicator": indicator, "series": series, "rows": rows})
        return payloads

    async def _read(self, client, params: dict) -> list[list]:
        rows, offset, total = [], 0, None
        while total is None or offset < total:
            body = (await get_with_retry(
                client, f"{self.source.base_url}/series/", params=params | {"start": offset},
            )).json()
            total = int(body.get("count") or 0)
            page = body.get("data") or []
            if not page:
                break
            rows.extend(page)
            offset += len(page)
        return rows

    def to_canonical(self, raw_payload: dict) -> list[CanonicalRecord]:
        indicator, series = raw_payload["indicator"], raw_payload["series"]
        rows = [(date.fromisoformat(d), float(v)) for d, v in raw_payload["rows"] if v is not None]
        if series.transform == "pct_change_year_ago":
            rows = pct_change_year_ago(rows)
        return [
            CanonicalRecord(
                indicator_code=indicator.code,
                country_iso3=self.options["country"],
                period=period_label(d, series.frequency),
                frequency=series.frequency,
                value=v * series.scale,
                unit=indicator.unit,
            )
            for d, v in rows
        ]
