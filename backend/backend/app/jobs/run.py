"""Run ingestion from the command line (also what a cron job calls in deployment).

    python -m app.jobs.run --source world_bank
    python -m app.jobs.run --all
    python -m app.jobs.run --source ilostat --since 2015
"""
import argparse

from app.core.config_files import sources
from app.core.database import SessionLocal
from app.ingestion.pipeline import run_source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source", help="source_code from config/sources.yaml")
    group.add_argument("--all", action="store_true", help="every source with a connector")
    parser.add_argument("--since", type=int, help="first year to fetch (default: per source)")
    parser.add_argument("--triggered-by", default="manual", choices=["manual", "scheduler"])
    args = parser.parse_args()

    codes = [args.source] if args.source else [s.source_code for s in sources().sources if s.connector]
    with SessionLocal() as session:
        for code in codes:
            run = run_source(session, code, args.triggered_by, args.since)
            print(f"{code}: {run.status} | fetched {run.records_fetched} | "
                  f"normalized {run.records_normalized}"
                  + (f" | {run.error_message}" if run.error_message else ""))


if __name__ == "__main__":
    main()
