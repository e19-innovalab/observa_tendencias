"""Build the Ludita indicator and store it per reference year.

Same engine as the Moctezuma indicator (app/analytics/moctezuma.py): exposure to generative AI
pushes the score up and vitality (employment and training growth) holds it back. Each scored
occupation also gets its path: the quadrant of exposure and vitality (config/analytics.yaml,
section ludita).
"""
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.analytics.moctezuma_run import two_sided_results
from app.core.config_files import analytics_params
from app.models import LuditaScore, Methodology

SECTION = "ludita"


def sides() -> tuple[str, str]:
    push, counter = analytics_params(SECTION)["sides"]
    return push, counter


def path_for(components: dict, counter: str, paths: dict) -> str | None:
    """Quadrant on raw values. weaver: exposed and the market moves away; teller: exposed and the
    market keeps betting on it; other_causes: little exposed but shrinking; out_of_reach: little
    exposed and growing. None without exposure or without any vitality dimension."""
    exposure = components[paths["exposure_dimension"]]["raw"]
    growth = [(c["raw"], c["weight"]) for c in components.values()
              if c["side"] == counter and c["raw"] is not None]
    if exposure is None or not growth:
        return None
    vitality = sum(v * w for v, w in growth) / sum(w for _, w in growth)
    retreat = vitality < paths["retreat_below"]
    if exposure >= paths["exposed_from"]:
        return "weaver" if retreat else "teller"
    return "other_causes" if retreat else "out_of_reach"


def recompute_ludita(session: Session, method: Methodology) -> int:
    """Recalculate every reference year. Returns the number of scores stored."""
    push, counter = sides()
    paths = analytics_params(SECTION)["paths"]
    now = datetime.now(UTC)
    session.execute(delete(LuditaScore).where(LuditaScore.methodology_id == method.methodology_id))
    stored = 0
    for country, occ, year, res in two_sided_results(session, SECTION, (push, counter)):
        session.add(LuditaScore(
            country_iso3=country, occupation_code=occ, year=year, score=res["score"],
            level=res["level"],
            path=path_for(res["components"], counter, paths) if res["score"] is not None else None,
            exposure=res[push], vitality=res[counter],
            exposure_coverage=res["coverage"][push], vitality_coverage=res["coverage"][counter],
            components=res["components"], methodology_id=method.methodology_id, computed_at=now,
        ))
        stored += 1
    return stored
