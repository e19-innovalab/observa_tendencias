"""Load the processed analytics CSVs into Postgres (idempotent upsert).

    python -m app.ingestion.load_analytics

Reads the file listed under paths in config/app.yaml: jobs -> job_postings.
Needs DATABASE_URL in backend/.env.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.core.config_files import app_config
from app.core.database import SessionLocal
from app.models import JobPosting

PATHS = app_config().paths
ENCODING = PATHS.csv_encoding


def _clean(df: pd.DataFrame) -> list[dict]:
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict("records")


def read_jobs(path: Path = PATHS.processed_file("jobs")) -> list[dict]:
    df = pd.read_csv(path, encoding=ENCODING, dtype={"id": str})
    df["fecha_publicacion"] = pd.to_datetime(df["fecha_publicacion"]).dt.date
    df["postulantes"] = pd.to_numeric(df["postulantes"], errors="coerce").astype("Int64")
    df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True)
    return _clean(df)


def upsert(session, model, rows: list[dict], keys: list[str]) -> None:
    stmt = insert(model)
    update = {c.name: stmt.excluded[c.name] for c in model.__table__.columns if c.name not in keys}
    session.execute(stmt.on_conflict_do_update(index_elements=keys, set_=update), rows)


def main() -> None:
    jobs = read_jobs()
    with SessionLocal() as session:
        upsert(session, JobPosting, jobs, ["id"])
        session.commit()
    print(f"job_postings: {len(jobs)}")


if __name__ == "__main__":
    main()
