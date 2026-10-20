"""Skill gaps (plan 8.4): demand vs. supply, both on a 0-100 scale."""

from app.core.config_files import analytics_params


def data_sufficiency(demand: float | None, supply: float | None) -> str:
    if demand is not None and supply is not None:
        return "full"
    if demand is not None or supply is not None:
        return "partial"
    return "none"


def compute_skill_gaps(
    skills: dict[str, dict[str, float | None]], params: dict | None = None
) -> list[dict]:
    """skills: {skill_code: {demand, supply, demand_growth}} with demand/supply in 0-100.

    gap_score = demand - supply. If either side is missing gap_score is None; we never
    invent a gap (data_sufficiency tells the API what to say).
    """
    p = analytics_params("skill_gaps", params)
    out = []
    for code, v in skills.items():
        demand, supply, growth = v.get("demand"), v.get("supply"), v.get("demand_growth")
        suff = data_sufficiency(demand, supply)
        out.append(
            {
                "skill_code": code,
                "demand_score": demand,
                "supply_score": supply,
                "gap_score": demand - supply if suff == "full" else None,
                "is_emerging": growth is not None and growth > p["emerging_growth"],
                "data_sufficiency": suff,
            }
        )
    return sorted(out, key=lambda r: (r["gap_score"] is None, -(r["gap_score"] or 0)))
