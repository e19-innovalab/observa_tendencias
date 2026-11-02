"""Roll occupation values up to occupation groups for the "ocupaciones en movimiento" chart.

Occupation series are stored once per catalog occupation, but every occupation of a source group
(the ISCO digits the series is published at) shares the group value. Rolling up therefore counts
each source group once: the group value is the sum (e.g. employment) or mean (e.g. earnings) of
its source groups.
"""
from collections import defaultdict
from statistics import fmean
from typing import Literal

from app.analytics.employability_run import Point

Key = tuple[str, str, int]  # (country, group, year)


def roll_up(points: dict[tuple[str, str], list[Point]], source_digits: dict[str, int],
            group_digits: int, aggregate: Literal["sum", "mean"],
            all_years: list[int] | None = None) -> dict[Key, float]:
    """points: (country, occupation) -> points. source_digits: country -> digits of the source
    groups. all_years: when given, the latest value of each occupation applies to these years
    (characteristics that are not yearly measurements)."""
    by_source: dict[tuple[str, str, int], float] = {}
    for (country, occ), pts in points.items():
        if not pts:
            continue
        source = occ[:source_digits.get(country, len(occ))]
        years = [(y, pts[-1].value) for y in all_years] if all_years is not None \
            else [(p.year, p.value) for p in pts]
        for year, value in years:
            by_source.setdefault((country, source, year), value)
    grouped: dict[Key, list[float]] = defaultdict(list)
    for (country, source, year), value in by_source.items():
        grouped[(country, source[:group_digits], year)].append(value)
    agg = sum if aggregate == "sum" else fmean
    return {k: agg(v) for k, v in grouped.items()}


def year_over_year(values: dict[Key, float], min_base: float = 0) -> dict[Key, float]:
    """Percent change against the previous year, when both years exist and the base is positive
    and at least min_base."""
    return {(c, g, y): (v / base - 1) * 100 for (c, g, y), v in values.items()
            if (base := values.get((c, g, y - 1))) is not None and base > 0 and base >= min_base}


def with_carry(values: dict[Key, float], key: Key, max_years: int) -> tuple[float, int] | None:
    """Value for key, or the latest one at most max_years older. Returns (value, year used)."""
    country, group, year = key
    for back in range(max_years + 1):
        if (v := values.get((country, group, year - back))) is not None:
            return v, year - back
    return None
