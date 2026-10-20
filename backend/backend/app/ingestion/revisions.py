"""Keep the previous value of source data when a load changes or removes it (data_revisions).

Loads replace data in place (upserts, or delete-and-insert of a whole file), so without this a
source's revision would overwrite what was published before. Each loader passes the values it
is about to replace and the ones it writes; only real differences are recorded.
"""
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models import DataRevision

# Fields identifying an observation (the observations unique key).
OBSERVATION_KEY = [
    "indicator_code", "country_iso3", "sector_code", "occupation_code",
    "period_start", "frequency", "data_type", "source_id",
]
# Relative difference below which two values are the same number (float noise).
TOLERANCE = 1e-9


def _plain(value):
    return value.isoformat() if isinstance(value, date) else value


def record_changes(session: Session, dataset: str, source_id: int, run_id: int | None,
                   key_fields: list[str], old: dict[tuple, tuple[float, int | None]],
                   new: dict[tuple, float], removals: bool) -> int:
    """old: {key: (value, run that wrote it)}; new: {key: value}. A key in both with another
    value is "revised"; a key only in old is "removed" when the load replaces the whole set
    (removals=True), not when it only brings part of it (an API returning recent years)."""
    now, out = datetime.now(UTC), []
    for key, (old_value, old_run) in old.items():
        if key in new:
            new_value = new[key]
            if old_value is None and new_value is None:
                continue
            if old_value is not None and new_value is not None and abs(new_value - old_value) <= \
                    TOLERANCE * max(1.0, abs(old_value)):
                continue
            change = "revised"
        elif removals:
            new_value, change = None, "removed"
        else:
            continue
        out.append(DataRevision(
            dataset=dataset, source_id=source_id, run_id=run_id, old_run_id=old_run,
            record_key={k: _plain(v) for k, v in zip(key_fields, key, strict=True)},
            change=change, old_value=old_value, new_value=new_value, revised_at=now))
    session.add_all(out)
    return len(out)
