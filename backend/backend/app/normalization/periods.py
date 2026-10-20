"""Period handling: source period strings -> (period_start, period_end) and back to labels.

Frequencies: A (annual, "2024"), Q (quarterly, "2024-Q2" or "2024Q2"), M (monthly, "2024-03"
or "2024M03"). Values are stored at their native frequency; aggregation happens at query time.
"""
import calendar
import re
from datetime import date

_QUARTER = re.compile(r"^(\d{4})-?Q([1-4])$")
_MONTH = re.compile(r"^(\d{4})-?M?(\d{2})$")
_MONTHS_PER_QUARTER = 3


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def to_period_range(period: str, frequency: str) -> tuple[date, date]:
    period = period.strip()
    if frequency == "A":
        year = int(period[:4])
        return date(year, 1, 1), date(year, 12, 31)
    if frequency == "Q":
        m = _QUARTER.match(period)
        if not m:
            raise ValueError(f"Unrecognized quarterly period: {period!r}")
        year, q = int(m.group(1)), int(m.group(2))
        first = (q - 1) * _MONTHS_PER_QUARTER + 1
        return date(year, first, 1), _month_end(year, first + _MONTHS_PER_QUARTER - 1)
    if frequency == "M":
        m = _MONTH.match(period)
        if not m:
            raise ValueError(f"Unrecognized monthly period: {period!r}")
        year, month = int(m.group(1)), int(m.group(2))
        return date(year, month, 1), _month_end(year, month)
    raise ValueError(f"Unsupported frequency: {frequency!r}")


def period_label(start: date, frequency: str) -> str:
    if frequency == "A":
        return f"{start.year}"
    if frequency == "Q":
        return f"{start.year}-Q{(start.month - 1) // _MONTHS_PER_QUARTER + 1}"
    if frequency == "M":
        return f"{start.year}-{start.month:02d}"
    raise ValueError(f"Unsupported frequency: {frequency!r}")


def shift_period(start: date, frequency: str, steps: int) -> tuple[date, date]:
    """Period `steps` periods after the one starting at `start` (used for projections)."""
    months = {"A": 12, "Q": _MONTHS_PER_QUARTER, "M": 1}[frequency] * steps
    index = start.year * 12 + start.month - 1 + months
    year, month = divmod(index, 12)
    new_start = date(year, month + 1, 1)
    return to_period_range(period_label(new_start, frequency), frequency)
