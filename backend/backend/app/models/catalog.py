from sqlalchemy import ARRAY, JSON, Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Country(Base):
    __tablename__ = "countries"
    iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    name_es: Mapped[str] = mapped_column(Text)
    name_en: Mapped[str] = mapped_column(Text)


class Sector(Base):
    __tablename__ = "sectors"
    sector_code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    isic_codes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)


class Occupation(Base):
    """ISCO-08 unit group; occupation_code is the ISCO-08 code. Featured occupations are the ones
    shown by default and the only ones with a strategic sector."""

    __tablename__ = "occupations"
    occupation_code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    name_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    isco08_code: Mapped[str] = mapped_column(Text)
    sector_code: Mapped[str | None] = mapped_column(ForeignKey("sectors.sector_code"), nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    exclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class OccupationCrosswalk(Base):
    __tablename__ = "occupation_crosswalks"
    country_iso3: Mapped[str] = mapped_column(ForeignKey("countries.iso3"), primary_key=True)
    national_system: Mapped[str] = mapped_column(Text, primary_key=True)
    national_code: Mapped[str] = mapped_column(Text, primary_key=True)
    isco08_code: Mapped[str] = mapped_column(Text)


class Skill(Base):
    __tablename__ = "skills"
    skill_code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    skill_type: Mapped[str | None] = mapped_column(Text)
    esco_uri: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)  # definition shown (Spanish)
    description_en: Mapped[str | None] = mapped_column(Text)  # ESCO's English original
    # where the Spanish comes from: esco (ESCO's own Spanish) | translation
    # (config/reference/esco_traducciones_es.yaml, kept next to the English original)
    description_origin: Mapped[str | None] = mapped_column(Text)
    # ESCO hierarchy group at analytics.yaml -> skill_gaps.group_level (e.g. S2.2.1, or a CINE-F
    # detailed field such as 0412 for knowledge)
    group_code: Mapped[str | None] = mapped_column(Text)


class SkillGroup(Base):
    """A concept of the ESCO skills hierarchy (skills S, attitudes A, languages L, transversal T;
    knowledge follows CINE-F/ISCED-F fields). Parents are kept so groups can be rolled up."""

    __tablename__ = "skill_groups"
    group_code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)  # shown (Spanish)
    description_en: Mapped[str | None] = mapped_column(Text)  # ESCO's English original
    description_origin: Mapped[str | None] = mapped_column(Text)  # esco | translation
    level: Mapped[int] = mapped_column()
    parent_code: Mapped[str | None] = mapped_column(Text)
    esco_uri: Mapped[str | None] = mapped_column(Text)


class OccupationSkill(Base):
    __tablename__ = "occupation_skills"
    occupation_code: Mapped[str] = mapped_column(ForeignKey("occupations.occupation_code"), primary_key=True)
    skill_code: Mapped[str] = mapped_column(ForeignKey("skills.skill_code"), primary_key=True)
    country_iso3: Mapped[str] = mapped_column(ForeignKey("countries.iso3"), primary_key=True)
    weight: Mapped[float | None] = mapped_column(Numeric)
    # ESCO category for the group: "essential" if essential for at least one of the group's ESCO
    # occupations, otherwise "optional" (sources.yaml -> esco.options.relation_categories)
    relation: Mapped[str | None] = mapped_column(String(16))
    # The group's ESCO occupations that use the skill and how: [{"name", "relation"}], strongest
    # first (e.g. 7515 food tasters, via "controlador de leche de granja", essential)
    via: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.source_id"))
