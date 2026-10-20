"""World Bank Indicators API (REST JSON, no authentication).

GET {base_url}/country/{ARG;URY;CHL}/indicator/{id}?format=json&per_page=&date=start:end
Response: [meta, rows]; meta.lastupdated is the source update date.
"""
from datetime import date

from app.connectors.base import BaseConnector, CanonicalRecord, SeriesSpec
from app.connectors.http import get_with_retry, make_client


class WorldBankConnector(BaseConnector):
    async def fetch(self, specs: list[SeriesSpec], since_year: int | None) -> list[dict]:
        countries = self.options["country_separator"].join(self.countries)
        start = since_year or self.options["start_year"]
        payloads = []
        async with make_client() as client:
            for indicator, series in specs:
                url = f"{self.source.base_url}/country/{countries}/indicator/{series.id}"
                rows, meta, page, pages = [], {}, 1, 1
                while page <= pages:
                    params = {
                        "format": "json",
                        "per_page": self.options["per_page"],
                        "date": f"{start}:{date.today().year}",
                        "page": page,
                    }
                    body = (await get_with_retry(client, url, params=params)).json()
                    meta = body[0]
                    pages = int(meta.get("pages") or 1)
                    rows.extend(body[1] or [])
                    page += 1
                payloads.append(
                    {"indicator": indicator, "series": series, "meta": meta, "rows": rows}
                )
        return payloads

    def to_canonical(self, raw_payload: dict) -> list[CanonicalRecord]:
        indicator, series = raw_payload["indicator"], raw_payload["series"]
        updated = raw_payload["meta"].get("lastupdated")
        source_updated_at = date.fromisoformat(updated) if updated else None
        records = []
        for row in raw_payload["rows"]:
            if row.get("value") is None or row.get("countryiso3code") not in self.countries:
                continue
            records.append(
                CanonicalRecord(
                    indicator_code=indicator.code,
                    country_iso3=row["countryiso3code"],
                    period=str(row["date"]),
                    frequency=series.frequency,
                    value=float(row["value"]),
                    unit=indicator.unit,
                    source_updated_at=source_updated_at,
                )
            )
        return records
