from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
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


class MoctezumaScore(Base):
    """Moctezuma indicator per country, occupation and reference year: technological pace vs
    capacity to respond (both 0-100 within the cohort). gap = pace − readiness. components holds,
    per dimension, its side, raw and scaled value, weight and where it came from."""

    __tablename__ = "moctezuma_scores"
    __table_args__ = (
        UniqueConstraint("country_iso3", "occupation_code", "year", "methodology_id",
                         name="uq_moctezuma_scores_key"),
    )
    score_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_iso3: Mapped[str] = mapped_column(String(3), ForeignKey("countries.iso3"))
    occupation_code: Mapped[str] = mapped_column(ForeignKey("occupations.occupation_code"))
    year: Mapped[int] = mapped_column(Integer)
    score: Mapped[float | None] = mapped_column(Float)
    level: Mapped[str] = mapped_column(Text)
    pace: Mapped[float | None] = mapped_column(Float)
    readiness: Mapped[float | None] = mapped_column(Float)
    gap: Mapped[float | None] = mapped_column(Float)
    pace_coverage: Mapped[float] = mapped_column(Float)
    readiness_coverage: Mapped[float] = mapped_column(Float)
    components: Mapped[dict] = mapped_column(JsonType)
    methodology_id: Mapped[int] = mapped_column(ForeignKey("methodologies.methodology_id"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LuditaScore(Base):
    """Ludita indicator per country, occupation and reference year: exposure to generative AI vs
    vitality (employment and training growth), both 0-100 within the cohort. path is the
    quadrant (weaver, teller, other_causes, out_of_reach). components as in MoctezumaScore."""

    __tablename__ = "ludita_scores"
    __table_args__ = (
        UniqueConstraint("country_iso3", "occupation_code", "year", "methodology_id",
                         name="uq_ludita_scores_key"),
    )
    score_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_iso3: Mapped[str] = mapped_column(String(3), ForeignKey("countries.iso3"))
    occupation_code: Mapped[str] = mapped_column(ForeignKey("occupations.occupation_code"))
    year: Mapped[int] = mapped_column(Integer)
    score: Mapped[float | None] = mapped_column(Float)
    level: Mapped[str] = mapped_column(Text)
    path: Mapped[str | None] = mapped_column(Text)
    exposure: Mapped[float | None] = mapped_column(Float)
    vitality: Mapped[float | None] = mapped_column(Float)
    exposure_coverage: Mapped[float] = mapped_column(Float)
    vitality_coverage: Mapped[float] = mapped_column(Float)
    components: Mapped[dict] = mapped_column(JsonType)
    methodology_id: Mapped[int] = mapped_column(ForeignKey("methodologies.methodology_id"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SkillProfile(Base):
    """What one source lists for an ISCO-08 unit group in one of its versions (O*NET technologies,
    ESCO skills). Every version is kept: the Reina Roja indicator compares them."""

    __tablename__ = "skill_profiles"
    __table_args__ = (
        UniqueConstraint("source_code", "version", "occupation_code", name="uq_skill_profiles_key"),
    )
    profile_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_code: Mapped[str] = mapped_column(ForeignKey("sources.source_code"))
    version: Mapped[str] = mapped_column(Text)
    released: Mapped[date] = mapped_column(Date)
    occupation_code: Mapped[str] = mapped_column(ForeignKey("occupations.occupation_code"))
    items: Mapped[dict] = mapped_column(JsonType)  # {item key: display name}
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RedQueenScore(Base):
    """Reina Roja indicator per occupation and reference year: how much of its profile changes per
    year (not country-specific). components holds, per source, the pair of versions compared,
    the annual turnover, the half-life and examples of what entered and left."""

    __tablename__ = "red_queen_scores"
    __table_args__ = (
        UniqueConstraint("occupation_code", "year", "methodology_id", name="uq_red_queen_scores_key"),
    )
    score_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    occupation_code: Mapped[str] = mapped_column(ForeignKey("occupations.occupation_code"))
    year: Mapped[int] = mapped_column(Integer)
    score: Mapped[float | None] = mapped_column(Float)
    level: Mapped[str] = mapped_column(Text)
    turnover: Mapped[float | None] = mapped_column(Float)  # weighted mean annual turnover
    half_life: Mapped[float | None] = mapped_column(Float)  # years, from turnover
    coverage: Mapped[float] = mapped_column(Float)
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
        Index("ix_skill_gaps_method_country_year", "methodology_id", "country_iso3", "year"),
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


class SkillGroupGap(Base):
    """Gap per country, ESCO skill group and year: same method as SkillGap, over the occupations
    that use any skill of the group (each occupation weighs as its strongest skill of the group)."""

    __tablename__ = "skill_group_gaps"
    __table_args__ = (
        UniqueConstraint("country_iso3", "group_code", "year", "methodology_id",
                         name="uq_skill_group_gaps_key"),
        Index("ix_skill_group_gaps_method_country_year", "methodology_id", "country_iso3", "year"),
    )
    gap_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_iso3: Mapped[str] = mapped_column(String(3), ForeignKey("countries.iso3"))
    group_code: Mapped[str] = mapped_column(ForeignKey("skill_groups.group_code"))
    year: Mapped[int] = mapped_column(Integer)
    demand_growth: Mapped[float | None] = mapped_column(Float)
    supply_growth: Mapped[float | None] = mapped_column(Float)
    gap: Mapped[float | None] = mapped_column(Float)
    is_emerging: Mapped[bool] = mapped_column(Boolean, default=False)
    data_sufficiency: Mapped[str] = mapped_column(Text)
    demand_coverage: Mapped[float] = mapped_column(Float)
    supply_coverage: Mapped[float] = mapped_column(Float)
    occupations: Mapped[int] = mapped_column(Integer)
    skills: Mapped[int] = mapped_column(Integer)  # member skills used by at least one occupation
    details: Mapped[dict] = mapped_column(JsonType)
    methodology_id: Mapped[int] = mapped_column(ForeignKey("methodologies.methodology_id"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
