"""Load the processed analytics CSVs into Postgres (idempotent upsert).

    python -m app.ingestion.load_analytics

Reads the files listed under paths in config/app.yaml:
       coverage -> coverage_report, jobs -> job_postings,
       graduate_trends -> graduate_trends, graduate_projections -> graduate_projections
Needs DATABASE_URL in backend/.env.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.core.config_files import app_config
from app.core.database import SessionLocal
from app.models import CoverageReport, GraduateProjection, GraduateTrend, JobPosting

PATHS = app_config().paths
ENCODING = PATHS.csv_encoding


def _clean(df: pd.DataFrame) -> list[dict]:
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict("records")


def read_coverage(path: Path = PATHS.processed_file("coverage")) -> list[dict]:
    df = pd.read_csv(path, encoding=ENCODING)
    for col in ("anio_min", "anio_max"):
        df[col] = df[col].astype("Int64")
    df["elegible_proyeccion"] = df["elegible_proyeccion"].astype(bool)
    return _clean(df)


def read_jobs(path: Path = PATHS.processed_file("jobs")) -> list[dict]:
    df = pd.read_csv(path, encoding=ENCODING, dtype={"id": str})
    df["fecha_publicacion"] = pd.to_datetime(df["fecha_publicacion"]).dt.date
    df["postulantes"] = pd.to_numeric(df["postulantes"], errors="coerce").astype("Int64")
    df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True)
    return _clean(df)


def read_graduate_trends(path: Path = PATHS.processed_file("graduate_trends")) -> list[dict]:
    df = pd.read_csv(path, encoding=ENCODING)
    df["tiene_huecos"] = df["tiene_huecos"].astype(bool)
    return _clean(df[[c.name for c in GraduateTrend.__table__.columns]])


def read_graduate_projections(path: Path = PATHS.processed_file("graduate_projections")) -> list[dict]:
    df = pd.read_csv(path, encoding=ENCODING)
    return _clean(df[[c.name for c in GraduateProjection.__table__.columns]])


def upsert(session, model, rows: list[dict], keys: list[str]) -> None:
    stmt = insert(model)
    update = {c.name: stmt.excluded[c.name] for c in model.__table__.columns if c.name not in keys}
    session.execute(stmt.on_conflict_do_update(index_elements=keys, set_=update), rows)


def main() -> None:
    coverage, jobs = read_coverage(), read_jobs()
    trends, projections = read_graduate_trends(), read_graduate_projections()
    with SessionLocal() as session:
        upsert(session, CoverageReport, coverage, ["pais", "sector"])
        upsert(session, JobPosting, jobs, ["id"])
        upsert(session, GraduateTrend, trends, ["pais", "nombre"])
        upsert(session, GraduateProjection, projections, ["pais", "nombre", "anio"])
        session.commit()
    print(
        f"coverage_report: {len(coverage)} | job_postings: {len(jobs)} | "
        f"graduate_trends: {len(trends)} | graduate_projections: {len(projections)}"
    )


if __name__ == "__main__":
    main()
