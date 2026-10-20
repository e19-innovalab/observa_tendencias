"""Canonical records -> observation rows. Records that cannot be mapped are reported, not dropped
silently (plan 7)."""
from dataclasses import dataclass, field
from datetime import datetime

from app.connectors.base import CanonicalRecord
from app.core.config_files import catalog, indicators
from app.normalization.periods import to_period_range


@dataclass
class NormalizationResult:
    rows: list[dict] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def normalize(
    records: list[CanonicalRecord],
    source_id: int,
    run_id: int | None,
    fetched_at: datetime,
    data_type: str = "observed",
) -> NormalizationResult:
    cat = catalog()
    countries = {c.iso3 for c in cat.countries}
    sectors = {s.sector_code for s in cat.sectors}
    occupations = {o.occupation_code for o in cat.occupations}
    known_indicators = {i.code for i in indicators().indicators}

    result = NormalizationResult()
    for r in records:
        if r.indicator_code not in known_indicators:
            result.issues.append(f"indicador desconocido {r.indicator_code}")
            continue
        if r.country_iso3 not in countries:
            result.issues.append(f"país fuera del catálogo {r.country_iso3}")
            continue
        if r.sector_code is not None and r.sector_code not in sectors:
            result.issues.append(f"sector fuera del catálogo {r.sector_code}")
            continue
        if r.occupation_code is not None and r.occupation_code not in occupations:
            result.issues.append(f"ocupación fuera del catálogo {r.occupation_code}")
            continue
        try:
            start, end = to_period_range(r.period, r.frequency)
        except ValueError as exc:
            result.issues.append(str(exc))
            continue
        result.rows.append(
            {
                "indicator_code": r.indicator_code,
                "country_iso3": r.country_iso3,
                "sector_code": r.sector_code,
                "occupation_code": r.occupation_code,
                "period_start": start,
                "period_end": end,
                "frequency": r.frequency,
                "value": r.value,
                "unit": r.unit,
                "data_type": data_type,
                "source_id": source_id,
                "run_id": run_id,
                "source_updated_at": r.source_updated_at,
                "fetched_at": fetched_at,
            }
        )
    return result
