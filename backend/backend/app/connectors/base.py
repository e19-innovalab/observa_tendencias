from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel

from app.core.config_files import IndicatorConf, SeriesConf, SourceConf

SeriesSpec = tuple[IndicatorConf, SeriesConf]


class CanonicalRecord(BaseModel):
    indicator_code: str
    country_iso3: str
    sector_code: str | None = None
    occupation_code: str | None = None
    period: str
    frequency: str
    value: float
    unit: str
    source_updated_at: date | None = None


class SourceHealth(BaseModel):
    ok: bool
    detail: str = ""


class BaseConnector(ABC):
    """One connector per source. Endpoints and options come from config/sources.yaml and the
    series to fetch from config/indicators.yaml, so adding a series needs no code changes."""

    def __init__(self, source: SourceConf, countries: list[str]):
        self.source = source
        self.countries = countries

    @property
    def options(self) -> dict:
        return self.source.options

    @abstractmethod
    async def fetch(self, specs: list[SeriesSpec], since_year: int | None) -> list[dict]:
        """Call the external source and return raw payloads (one per series)."""

    @abstractmethod
    def to_canonical(self, raw_payload: dict) -> list[CanonicalRecord]:
        """Map one raw payload to canonical records (not yet saved)."""

    def education_cells(self, raw_payload: dict) -> list[dict]:
        """Employment by occupation group and education band behind an education-mismatch
        series (EducationMismatchCell rows without the run fields). Other sources: none."""
        return []

    async def health_check(self) -> SourceHealth:
        """Lightweight request to check availability."""
        return SourceHealth(ok=True)
