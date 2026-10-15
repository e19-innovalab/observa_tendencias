from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CoverageReport(Base):
    """Rows of data/processed/data_analytics/informe_cobertura.csv."""

    __tablename__ = "coverage_report"
    pais: Mapped[str] = mapped_column(String(3), primary_key=True)
    sector: Mapped[str] = mapped_column(Text, primary_key=True)
    n_anios_observados: Mapped[int] = mapped_column(Integer)
    anio_min: Mapped[int | None] = mapped_column(Integer)
    anio_max: Mapped[int | None] = mapped_column(Integer)
    elegible_proyeccion: Mapped[bool] = mapped_column(Boolean)
    estado: Mapped[str] = mapped_column(Text)


class JobPosting(Base):
    """Rows of data/processed/data_analytics/ofertas_linkedin.csv (LinkedIn, not official data)."""

    __tablename__ = "job_postings"
    __table_args__ = (Index("job_postings_filters", "pais", "provincia", "sector"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    pais: Mapped[str] = mapped_column(String(3))
    provincia: Mapped[str] = mapped_column(Text)
    sector: Mapped[str] = mapped_column(Text)
    regla_clasificacion: Mapped[str] = mapped_column(Text)
    titulo: Mapped[str] = mapped_column(Text)
    empresa: Mapped[str | None] = mapped_column(Text)
    ubicacion: Mapped[str | None] = mapped_column(Text)
    fecha_publicacion: Mapped[date | None] = mapped_column(Date)
    nivel_experiencia: Mapped[str | None] = mapped_column(Text)
    tipo_empleo: Mapped[str | None] = mapped_column(Text)
    industria: Mapped[str | None] = mapped_column(Text)
    postulantes: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(Text)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GraduateTrend(Base):
    """Rows of data/processed/data_analytics/egresados_tendencias.csv (graduates per career)."""

    __tablename__ = "graduate_trends"
    pais: Mapped[str] = mapped_column(Text, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, primary_key=True)
    anio_desde: Mapped[int] = mapped_column(Integer)
    anio_hasta: Mapped[int] = mapped_column(Integer)
    n_anios_serie: Mapped[int] = mapped_column(Integer)
    ventana_anios: Mapped[int] = mapped_column(Integer)
    graduados_inicio_ventana: Mapped[int] = mapped_column(Integer)
    graduados_ultimo: Mapped[int] = mapped_column(Integer)
    pendiente_normalizada: Mapped[float | None] = mapped_column(Float)
    variacion_ventana_pct: Mapped[float | None] = mapped_column(Float)
    tendencia: Mapped[str] = mapped_column(Text)
    tiene_huecos: Mapped[bool] = mapped_column(Boolean)
    proyeccion: Mapped[str] = mapped_column(Text)


class GraduateProjection(Base):
    """Rows of data/processed/data_analytics/egresados_proyecciones.csv (indicative)."""

    __tablename__ = "graduate_projections"
    pais: Mapped[str] = mapped_column(Text, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, primary_key=True)
    graduados_proyectado: Mapped[int] = mapped_column(Integer)
    limite_inferior: Mapped[int] = mapped_column(Integer)
    limite_superior: Mapped[int] = mapped_column(Integer)
