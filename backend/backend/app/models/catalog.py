from sqlalchemy import ARRAY, Boolean, ForeignKey, Numeric, String, Text
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


class OccupationSkill(Base):
    __tablename__ = "occupation_skills"
    occupation_code: Mapped[str] = mapped_column(ForeignKey("occupations.occupation_code"), primary_key=True)
    skill_code: Mapped[str] = mapped_column(ForeignKey("skills.skill_code"), primary_key=True)
    country_iso3: Mapped[str] = mapped_column(ForeignKey("countries.iso3"), primary_key=True)
    weight: Mapped[float | None] = mapped_column(Numeric)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.source_id"))
