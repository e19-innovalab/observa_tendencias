from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel


class CanonicalRecord(BaseModel):
    indicator_code: str
    country_iso3: str
    sector_code: str | None = None
    occupation_code: str | None = None
    period: str
    value: float
    unit: str
    source_updated_at: date | None = None


class SourceHealth(BaseModel):
    ok: bool
    detail: str = ""


class BaseConnector(ABC):
    source_code: str

    @abstractmethod
    async def fetch(self, series_ids: list[str], since: date | None) -> list[dict]:
        """Call the external source and return raw payloads."""

    @abstractmethod
    def to_canonical(self, raw_payload: dict) -> list[CanonicalRecord]:
        """Map one raw payload to canonical records (not yet saved)."""

    async def health_check(self) -> SourceHealth:
        """Lightweight request to check availability."""
        return SourceHealth(ok=True)
