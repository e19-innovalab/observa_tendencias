"""Recalculate trends and projections without fetching (e.g. after editing analytics.yaml).

    python -m app.jobs.recompute
    python -m app.jobs.recompute --indicator unemployment_rate --indicator inflation
"""
import argparse

from app.analytics.recompute import recompute
from app.core.database import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--indicator", action="append", help="indicator code (repeatable)")
    args = parser.parse_args()
    with SessionLocal() as session:
        summary = recompute(session, args.indicator)
        session.commit()
    print(f"series: {summary.series} | trends: {summary.trends} | "
          f"projection points: {summary.projections} | "
          f"employability scores: {summary.employability_scores} | "
          f"skill gaps: {summary.skill_gaps} | "
          f"moctezuma scores: {summary.moctezuma_scores} | "
          f"ludita scores: {summary.ludita_scores} | "
          f"reina roja scores: {summary.red_queen_scores} | new alerts: {summary.alerts}")


if __name__ == "__main__":
    main()
