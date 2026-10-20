"""Static reference tables kept in config/ (e.g. ILO generative-AI exposure by ISCO-08 code).

The table is read like any other source so its values reach observations with source and date.
Values are per occupation and do not vary by country: they are stored for every catalog country.
"""
from datetime import date

import yaml

from app.connectors.base import BaseConnector, CanonicalRecord, SeriesSpec
from app.core.config import settings
from app.core.config_files import catalog


class ReferenceTableConnector(BaseConnector):
    async def fetch(self, specs: list[SeriesSpec], since_year: int | None) -> list[dict]:
        payloads = []
        for indicator, series in specs:
            with (settings.config_dir / series.file).open(encoding="utf-8") as f:
                payloads.append({"indicator": indicator, "series": series, "table": yaml.safe_load(f)})
        return payloads

    def to_canonical(self, raw_payload: dict) -> list[CanonicalRecord]:
        indicator, series, table = (raw_payload[k] for k in ("indicator", "series", "table"))
        published = date.fromisoformat(table["published"]) if table.get("published") else None
        records = []
        for occ in catalog().occupations:
            row = table["values"].get(occ.isco08_code)
            if row is None or row.get(series.value_field) is None:
                continue
            for country in self.countries:
                records.append(CanonicalRecord(
                    indicator_code=indicator.code, country_iso3=country,
                    occupation_code=occ.occupation_code, period=str(table["reference_year"]),
                    frequency=series.frequency, value=float(row[series.value_field]),
                    unit=indicator.unit, source_updated_at=published,
                ))
        return records
