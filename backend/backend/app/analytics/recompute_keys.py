"""Which observed series exist: shared by the recompute and alert steps."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Observation


def observed_series_keys(session: Session, codes: list[str] | None) -> list[tuple]:
    """(indicator, country, sector, occupation, frequency) of every observed series."""
    stmt = select(
        Observation.indicator_code, Observation.country_iso3, Observation.sector_code,
        Observation.occupation_code, Observation.frequency,
    ).where(Observation.data_type == "observed").distinct()
    if codes:
        stmt = stmt.where(Observation.indicator_code.in_(codes))
    return list(session.execute(stmt).all())
