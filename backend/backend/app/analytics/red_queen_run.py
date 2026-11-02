"""Build the Reina Roja indicator from the stored skill profiles and store it per reference year.

For each source (dimension) the profiles of consecutive versions are compared per occupation;
each reference year uses the latest pair whose later version came out that year or up to
max_age_years before.
"""
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics.red_queen import (
    annual_turnover,
    compute_red_queen_index,
    half_life,
    reconcile,
    turnover,
)
from app.core.config_files import analytics_params, catalog
from app.models import Methodology, RedQueenScore, SkillProfile


def _compare(before: dict, after: dict, years: float, p: dict) -> dict:
    """Turnover between two profiles ({key: name}), annualized, with examples."""
    # same name under a new key (ESCO can give a skill a new code): the same item
    old_by_name = {v.casefold(): k for k, v in before.items() if k not in after}
    same_name = {k: old_by_name[v.casefold()] for k, v in after.items()
                 if k not in before and v.casefold() in old_by_name}
    after = {same_name.get(k, k): v for k, v in after.items()}
    renamed = reconcile(set(before), set(after), p["rename_min_chars"])
    names = {renamed.get(k, k): v for k, v in after.items()}
    a, b = set(before), set(names)
    total = turnover(a, b)
    annual = annual_turnover(total, years)
    return {"n_from": len(a), "n_to": len(b), "added_count": len(b - a),
            "new_per_year": len(b - a) / years,
            "removed_count": len(a - b), "renamed_count": len(renamed) + len(same_name), "turnover": total,
            "annual": annual, "half_life": half_life(annual, p["half_life_cap"]),
            "added": sorted(names[k] for k in b - a),
            "removed": sorted(before[k] for k in a - b)}


def profiles_by_version(session: Session, source_code: str) -> list[tuple]:
    """[(released, version, {occupation: items})], oldest first."""
    rows = session.scalars(select(SkillProfile).where(SkillProfile.source_code == source_code)).all()
    by_version: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        by_version[(r.released, r.version)][r.occupation_code] = r.items
    return [(d, v, occs) for (d, v), occs in sorted(by_version.items())]


def pair_for_year(versions: list[tuple], year: int, p: dict) -> tuple | None:
    """(earlier, later) versions for a reference year: the latest one published up to that year
    (no more than max_age_years before) and the latest one at least window_years older than it,
    or the oldest if that one is at least min_years older."""
    upto = [v for v in versions if v[0].year <= year and year - v[0].year <= p["max_age_years"]]
    if not upto:
        return None
    later = upto[-1]
    older = [v for v in versions if (later[0] - v[0]).days / 365.25 >= p["window_years"]]
    earlier = older[-1] if older else versions[0]
    if (later[0] - earlier[0]).days / 365.25 < p["min_years"]:
        return None
    return earlier, later


def recompute_red_queen(session: Session, method: Methodology) -> int:
    """Recalculate every reference year. Returns the number of scores stored."""
    p = analytics_params("red_queen")
    dims = p["dimensions"]
    versions = {d: profiles_by_version(session, c["source"]) for d, c in dims.items()}
    years = [v[0].year for vs in versions.values() for v in vs]
    if not years:
        return 0
    occupations = [o.occupation_code for o in catalog().occupations if not o.is_excluded]
    session.execute(delete(RedQueenScore).where(RedQueenScore.methodology_id == method.methodology_id))
    now = datetime.now(UTC)
    stored = 0
    for year in range(p["first_year"], max(years) + 1):
        pairs = {d: pair_for_year(versions[d], year, p) for d in dims}
        chosen: dict[str, dict[str, dict | None]] = {}
        for occ in occupations:
            chosen[occ] = {}
            for d, c in dims.items():
                pair = pairs[d]
                before = pair[0][2].get(occ) if pair else None
                after = pair[1][2].get(occ) if pair else None
                if before is None or after is None or len(before) < c["min_items"]:
                    chosen[occ][d] = None
                    continue
                (d0, v0, _), (d1, v1, _) = pair
                years_apart = (d1 - d0).days / 365.25
                chosen[occ][d] = {"from_version": v0, "to_version": v1,
                                  "from_date": d0.isoformat(), "to_date": d1.isoformat(),
                                  "years": round(years_apart, 2),
                                  **_compare(before, after, years_apart, p)}
        results = compute_red_queen_index(
            {occ: {d: (e if e else None) for d, e in by_dim.items()}
             for occ, by_dim in chosen.items()}, p)
        for occ, res in results.items():
            components = {d: {**(chosen[occ][d] or {}), "source": dims[d]["source"],
                              "weight": dims[d]["weight"], "normalized": res["normalized"][d],
                              "available": chosen[occ][d] is not None} for d in dims}
            session.add(RedQueenScore(
                occupation_code=occ, year=year, score=res["score"], level=res["level"],
                turnover=res["turnover"], half_life=res["half_life"], coverage=res["coverage"],
                components=components, methodology_id=method.methodology_id, computed_at=now))
            stored += 1
    return stored
