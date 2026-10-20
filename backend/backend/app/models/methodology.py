from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class Methodology(Base):
    """One row per distinct parameter set of a calculation (plan 4.4). Results point here, so a
    value can always be traced to the exact parameters that produced it."""

    __tablename__ = "methodologies"
    __table_args__ = (UniqueConstraint("methodology_type", "params_hash"),)
    methodology_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    methodology_type: Mapped[str] = mapped_column(Text)  # trend | projection | employability_index | alert
    version: Mapped[str] = mapped_column(Text)
    params: Mapped[dict] = mapped_column(JsonType)
    params_hash: Mapped[str] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(Text)
    description_md: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TrendResult(Base):
    """Trend state per series and window. History is kept (one row per window end), which is what
    the trend-reversal alert compares."""

    __tablename__ = "trend_results"
    __table_args__ = (
        UniqueConstraint(
            "indicator_code", "country_iso3", "sector_code", "occupation_code", "frequency",
            "window_end", "methodology_id",
            name="uq_trend_results_key", postgresql_nulls_not_distinct=True,
        ),
    )
    trend_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indicator_code: Mapped[str] = mapped_column(ForeignKey("indicators.indicator_code"))
    country_iso3: Mapped[str] = mapped_column(String(3), ForeignKey("countries.iso3"))
    sector_code: Mapped[str | None] = mapped_column(ForeignKey("sectors.sector_code"))
    occupation_code: Mapped[str | None] = mapped_column(ForeignKey("occupations.occupation_code"))
    frequency: Mapped[str] = mapped_column(Text)
    window_start: Mapped[date] = mapped_column(Date)
    window_end: Mapped[date] = mapped_column(Date)
    n_points: Mapped[int] = mapped_column(Integer)
    slope: Mapped[float | None] = mapped_column(Float)
    pct_change: Mapped[float | None] = mapped_column(Float)
    trend_state: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    methodology_id: Mapped[int] = mapped_column(ForeignKey("methodologies.methodology_id"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EmployabilityScore(Base):
    """Employability index (ISE) per country, occupation and reference year (plan 4.4).
    components holds, per dimension, the raw value, scaled value, weight and where it came from."""

    __tablename__ = "employability_scores"
    __table_args__ = (
        UniqueConstraint("country_iso3", "occupation_code", "year", "methodology_id",
                         name="uq_employability_scores_key"),
    )
    score_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_iso3: Mapped[str] = mapped_column(String(3), ForeignKey("countries.iso3"))
    occupation_code: Mapped[str] = mapped_column(ForeignKey("occupations.occupation_code"))
    year: Mapped[int] = mapped_column(Integer)
    score: Mapped[float | None] = mapped_column(Float)
    level: Mapped[str] = mapped_column(Text)
    coverage_ratio: Mapped[float] = mapped_column(Float)
    components: Mapped[dict] = mapped_column(JsonType)
    methodology_id: Mapped[int] = mapped_column(ForeignKey("methodologies.methodology_id"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Alert(Base):
    """Relevant change detected after an update (plan 4.4). dedupe_key makes each event unique:
    re-running the evaluation never records the same alert twice."""

    __tablename__ = "alerts"
    alert_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dedupe_key: Mapped[str] = mapped_column(Text, unique=True)
    alert_type: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)  # indicator | employability | source
    indicator_code: Mapped[str | None] = mapped_column(ForeignKey("indicators.indicator_code"))
    country_iso3: Mapped[str | None] = mapped_column(String(3), ForeignKey("countries.iso3"))
    sector_code: Mapped[str | None] = mapped_column(ForeignKey("sectors.sector_code"))
    occupation_code: Mapped[str | None] = mapped_column(ForeignKey("occupations.occupation_code"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.source_id"))
    period_label: Mapped[str | None] = mapped_column(Text)
    previous_value: Mapped[float | None] = mapped_column(Float)
    current_value: Mapped[float | None] = mapped_column(Float)
    previous_state: Mapped[str | None] = mapped_column(Text)
    current_state: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    methodology_id: Mapped[int | None] = mapped_column(ForeignKey("methodologies.methodology_id"))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class SkillGap(Base):
    """Skill gap per country, skill and reference year: demand growth vs supply growth (plan 4.4).
    Growth rates are fractions per year; gap is in the same unit (demand − supply)."""

    __tablename__ = "skill_gaps"
    __table_args__ = (
        UniqueConstraint("country_iso3", "skill_code", "year", "methodology_id",
                         name="uq_skill_gaps_key"),
    )
    gap_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_iso3: Mapped[str] = mapped_column(String(3), ForeignKey("countries.iso3"))
    skill_code: Mapped[str] = mapped_column(ForeignKey("skills.skill_code"))
    year: Mapped[int] = mapped_column(Integer)
    demand_growth: Mapped[float | None] = mapped_column(Float)
    supply_growth: Mapped[float | None] = mapped_column(Float)
    gap: Mapped[float | None] = mapped_column(Float)
    is_emerging: Mapped[bool] = mapped_column(Boolean, default=False)
    data_sufficiency: Mapped[str] = mapped_column(Text)  # full | partial | none
    demand_coverage: Mapped[float] = mapped_column(Float)
    supply_coverage: Mapped[float] = mapped_column(Float)
    occupations: Mapped[int] = mapped_column(Integer)
    details: Mapped[dict] = mapped_column(JsonType)
    methodology_id: Mapped[int] = mapped_column(ForeignKey("methodologies.methodology_id"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
