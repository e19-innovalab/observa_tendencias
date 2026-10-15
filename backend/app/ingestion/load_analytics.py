"""Load the processed analytics CSVs into Postgres (idempotent upsert).

    python -m app.ingestion.load_analytics

Reads  data/processed/data_analytics/informe_cobertura.csv       -> coverage_report
       data/processed/data_analytics/ofertas_linkedin.csv        -> job_postings
       data/processed/data_analytics/egresados_tendencias.csv    -> graduate_trends
       data/processed/data_analytics/egresados_proyecciones.csv  -> graduate_projections
Needs DATABASE_URL in backend/.env.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal
from app.models import CoverageReport, GraduateProjection, GraduateTrend, JobPosting

CSV_DIR = Path(__file__).resolve().parents[3] / "data" / "processed" / "data_analytics"


def _clean(df: pd.DataFrame) -> list[dict]:
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict("records")


def read_coverage(path: Path = CSV_DIR / "informe_cobertura.csv") -> list[dict]:
    df = pd.read_csv(path, encoding="utf-8-sig")
    for col in ("anio_min", "anio_max"):
        df[col] = df[col].astype("Int64")
    df["elegible_proyeccion"] = df["elegible_proyeccion"].astype(bool)
    return _clean(df)


def read_jobs(path: Path = CSV_DIR / "ofertas_linkedin.csv") -> list[dict]:
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"id": str})
    df["fecha_publicacion"] = pd.to_datetime(df["fecha_publicacion"]).dt.date
    df["postulantes"] = pd.to_numeric(df["postulantes"], errors="coerce").astype("Int64")
    df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True)
    return _clean(df)


def read_graduate_trends(path: Path = CSV_DIR / "egresados_tendencias.csv") -> list[dict]:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["tiene_huecos"] = df["tiene_huecos"].astype(bool)
    return _clean(df[[c.name for c in GraduateTrend.__table__.columns]])


def read_graduate_projections(path: Path = CSV_DIR / "egresados_proyecciones.csv") -> list[dict]:
    df = pd.read_csv(path, encoding="utf-8-sig")
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
