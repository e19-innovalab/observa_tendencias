from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Source(Base):
    __tablename__ = "sources"
    source_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(Text)  # api | dataset | manual
    base_url: Mapped[str | None] = mapped_column(Text)
    expected_frequency: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_normalized: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    triggered_by: Mapped[str] = mapped_column(Text)  # scheduler | manual | upload


class Indicator(Base):
    __tablename__ = "indicators"
    indicator_code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(Text)  # labor | economic | education
    higher_is_better: Mapped[bool | None] = mapped_column(Boolean)


class Observation(Base):
    """Single fact table (plan 4.3). data_type: observed | calculated | projected."""

    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint(
            "indicator_code", "country_iso3", "sector_code", "occupation_code",
            "period_start", "frequency", "data_type", "source_id",
            name="uq_observations_key", postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "data_type IN ('observed', 'calculated', 'projected')", name="ck_observations_data_type"
        ),
        Index("observations_lookup", "indicator_code", "country_iso3", "period_start"),
    )
    observation_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"),
                                                primary_key=True, autoincrement=True)
    indicator_code: Mapped[str] = mapped_column(ForeignKey("indicators.indicator_code"))
    country_iso3: Mapped[str] = mapped_column(String(3), ForeignKey("countries.iso3"))
    sector_code: Mapped[str | None] = mapped_column(ForeignKey("sectors.sector_code"))
    occupation_code: Mapped[str | None] = mapped_column(ForeignKey("occupations.occupation_code"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    frequency: Mapped[str] = mapped_column(Text)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(Text)
    data_type: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_runs.run_id"))
    methodology_id: Mapped[int | None] = mapped_column(Integer)
    lower_bound: Mapped[float | None] = mapped_column(Float)
    upper_bound: Mapped[float | None] = mapped_column(Float)
    source_updated_at: Mapped[date | None] = mapped_column(Date)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DatasetFile(Base):
    """Every official file read by the platform, downloaded or uploaded (plan 4.2,
    uploaded_datasets). Keeps the validation report, so any loaded value can be traced to the
    exact file and release, and rejected files explain why."""

    __tablename__ = "dataset_files"
    dataset_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_code: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    origin: Mapped[str] = mapped_column(Text)  # download | upload
    file_name: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    release: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"))
    stored_path: Mapped[str] = mapped_column(Text)
    # validated | rejected | loaded | replaced | format_changed | unchanged
    status: Mapped[str] = mapped_column(Text)
    report: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    records: Mapped[int] = mapped_column(Integer, default=0)
    declared_source_name: Mapped[str | None] = mapped_column(Text)
    declared_source_url: Mapped[str | None] = mapped_column(Text)
    reference_date: Mapped[date | None] = mapped_column(Date)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_runs.run_id"))
    replaces_dataset_id: Mapped[int | None] = mapped_column(ForeignKey("dataset_files.dataset_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    loaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EducationMismatchCell(Base):
    """Employed persons (thousands) by major occupation group and education band, the data behind
    the over/under-qualification indicators. status: matched | over | under | excluded (armed
    forces, occupation or education not stated)."""

    __tablename__ = "education_mismatch_cells"
    __table_args__ = (
        UniqueConstraint("country_iso3", "year", "isco_group", "band", "source_id",
                         name="uq_education_mismatch_cells"),
        CheckConstraint("status IN ('matched', 'over', 'under', 'excluded')",
                        name="ck_education_mismatch_cells_status"),
    )
    cell_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_iso3: Mapped[str] = mapped_column(String(3), ForeignKey("countries.iso3"))
    year: Mapped[int] = mapped_column(Integer)
    isco_group: Mapped[str] = mapped_column(Text)
    band: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    employed: Mapped[float] = mapped_column(Float)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_runs.run_id"))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DataRevision(Base):
    """Previous value of source data that a later load changed or removed, so a source's
    revisions are never lost. dataset: observations | graduates | education_mismatch_cells;
    record_key: the fields identifying the record; change: revised | removed."""

    __tablename__ = "data_revisions"
    __table_args__ = (
        CheckConstraint("change IN ('revised', 'removed')", name="ck_data_revisions_change"),
        Index("data_revisions_lookup", "dataset", "source_id", "revised_at"),
    )
    revision_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"),
                                             primary_key=True, autoincrement=True)
    dataset: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    record_key: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    change: Mapped[str] = mapped_column(Text)
    old_value: Mapped[float | None] = mapped_column(Float)
    new_value: Mapped[float | None] = mapped_column(Float)
    old_run_id: Mapped[int | None] = mapped_column(Integer)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_runs.run_id"))
    revised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
