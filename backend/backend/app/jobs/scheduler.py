"""Automatic updates: run every source with a connector on its schedule (plan 10).

    python -m app.jobs.scheduler            # keeps running; Ctrl+C to stop
    python -m app.jobs.scheduler --list     # show what would run and when

Schedules come from config/sources.yaml (scheduler.cron_by_frequency, or a source's own
`schedule`). In deployment the same jobs can run from the platform's cron instead:
`python -m app.jobs.run --source <code> --triggered-by scheduler`.
"""
import argparse
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.analytics.alerts_run import evaluate_stale_sources
from app.core.config_files import sources
from app.core.database import SessionLocal
from app.ingestion.pipeline import run_source

log = logging.getLogger("rumbo.scheduler")


def scheduled_sources() -> list[tuple[str, str]]:
    """(source_code, cron) for every source with a connector and a schedule."""
    conf = sources()
    out = []
    for s in conf.sources:
        cron = s.schedule or conf.scheduler.cron_by_frequency.get(s.expected_frequency or "")
        if s.connector and cron:
            out.append((s.source_code, cron))
    return out


def run_job(source_code: str) -> None:
    with SessionLocal() as session:
        run = run_source(session, source_code, "scheduler")
    log.info("%s: %s | %s registros | %s", source_code, run.status, run.records_normalized,
             run.error_message or "")


def stale_job() -> None:
    with SessionLocal() as session:
        added = evaluate_stale_sources(session)
        session.commit()
    log.info("fuentes desactualizadas: %s alertas nuevas", added)


def build_scheduler() -> BlockingScheduler:
    conf = sources().scheduler
    scheduler = BlockingScheduler(timezone=conf.timezone)
    for code, cron in scheduled_sources():
        scheduler.add_job(run_job, CronTrigger.from_crontab(cron, timezone=conf.timezone),
                          args=[code], id=f"source:{code}", coalesce=True, max_instances=1,
                          misfire_grace_time=conf.misfire_grace_seconds)
    scheduler.add_job(stale_job, CronTrigger.from_crontab(conf.stale_check_cron,
                                                          timezone=conf.timezone),
                      id="stale_sources", coalesce=True, max_instances=1,
                      misfire_grace_time=conf.misfire_grace_seconds)
    return scheduler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="show jobs and next run times")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    scheduler = build_scheduler()
    tz = sources().scheduler.timezone
    if args.list:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo(tz))
        for job in scheduler.get_jobs():
            print(f"{job.id:28s} {job.trigger}  próxima: {job.trigger.get_next_fire_time(None, now)}")
        return
    log.info("scheduler iniciado (%s): %s", tz, ", ".join(j.id for j in scheduler.get_jobs()))
    scheduler.start()


if __name__ == "__main__":
    main()
