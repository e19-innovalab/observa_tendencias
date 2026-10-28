from sqlalchemy import (
    Boolean,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DimPais(Base):
    """Dimension Pais (ARG, CHL, URY)."""

    __tablename__ = "dim_pais"
    pais_iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    pais_nombre: Mapped[str] = mapped_column(Text)


class DimSector(Base):
    """Dimension Sector Estrategico (5 sectores)."""

    __tablename__ = "dim_sector"
    sector: Mapped[str] = mapped_column(Text, primary_key=True)
    ciiu_rev4_divisiones: Mapped[str] = mapped_column(Text)


class DimTiempo(Base):
    """Dimension Tiempo (2007-2025)."""

    __tablename__ = "dim_tiempo"
    anio: Mapped[int] = mapped_column(Integer, primary_key=True)


class DimSexo(Base):
    """Dimension Sexo (T, F, M, NB, NS)."""

    __tablename__ = "dim_sexo"
    sexo_codigo: Mapped[str] = mapped_column(String(10), primary_key=True)
    sexo_descripcion: Mapped[str] = mapped_column(Text)


class DimCarrera(Base):
    """Dimension Carreras normalizadas."""

    __tablename__ = "dim_carrera"
    carrera_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    carrera_objetivo: Mapped[str] = mapped_column(Text)
    sector: Mapped[str] = mapped_column(Text)
    cine_f_codigo: Mapped[str] = mapped_column(String(10))
    nivel_esperado: Mapped[str] = mapped_column(Text)


class FactoresMacroPPA(Base):
    """Factores Macroeconomicos PPA e IPC armonizado (Banco Mundial e INDEC/INE)."""

    __tablename__ = "factores_macro_ppa"
    pais: Mapped[str] = mapped_column(String(3), primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, primary_key=True)
    factor_ppa: Mapped[float | None] = mapped_column(Float)
    metodo_ppa: Mapped[str | None] = mapped_column(Text)
    anio_base_ppa: Mapped[int | None] = mapped_column(Integer)
    ipc_base_2016: Mapped[float | None] = mapped_column(Float)
    ipc_original: Mapped[float | None] = mapped_column(Float)
    fuente_ipc: Mapped[str | None] = mapped_column(Text)
    base_original_ipc: Mapped[str | None] = mapped_column(Text)
    nota_metodologica: Mapped[str | None] = mapped_column(Text)


class FactEgresados(Base):
    """Tabla de hechos de egresados y titulados observados."""

    __tablename__ = "hecho_egresados"
    __table_args__ = (
        Index("ix_hecho_egresados_pais_sector_anio", "pais", "sector", "anio"),
        Index("ix_hecho_egresados_carrera", "carrera_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institucion: Mapped[str | None] = mapped_column(Text)
    carrera_id: Mapped[str | None] = mapped_column(Text)
    carrera_objetivo: Mapped[str | None] = mapped_column(Text)
    sector: Mapped[str | None] = mapped_column(Text)
    cine_f_codigo: Mapped[str | None] = mapped_column(Text)
    anio: Mapped[int] = mapped_column(Integer)
    nivel: Mapped[str | None] = mapped_column(Text)
    tipo_gestion: Mapped[str | None] = mapped_column(Text)
    sexo_raw: Mapped[str | None] = mapped_column(Text)
    valor: Mapped[float | None] = mapped_column(Float)
    sexo: Mapped[str | None] = mapped_column(String(10))
    pais: Mapped[str] = mapped_column(String(3))
    fuente_id: Mapped[str | None] = mapped_column(Text)
    nivel_granularidad: Mapped[str | None] = mapped_column(Text)
    calidad: Mapped[str | None] = mapped_column(Text)
    marca_quiebre_serie: Mapped[str | None] = mapped_column(Text)
    n_muestral: Mapped[float | None] = mapped_column(Float)
    es_observado: Mapped[bool] = mapped_column(Boolean, default=True)


class FactSalario(Base):
    """Tabla de hechos de salarios armonizados y convertidos a USD PPA."""

    __tablename__ = "hecho_salario"
    __table_args__ = (
        Index("ix_hecho_salario_pais_sector_anio", "pais", "sector", "anio"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pais: Mapped[str] = mapped_column(String(3))
    fuente_id: Mapped[str] = mapped_column(Text)
    sector: Mapped[str] = mapped_column(Text)
    carrera_id: Mapped[str | None] = mapped_column(Text)
    carrera_objetivo: Mapped[str | None] = mapped_column(Text)
    anio: Mapped[int] = mapped_column(Integer)
    sexo: Mapped[str] = mapped_column(String(10))
    salario_moneda_local: Mapped[float | None] = mapped_column(Float)
    moneda_local: Mapped[str | None] = mapped_column(String(10))
    factor_ppa: Mapped[float | None] = mapped_column(Float)
    salario_usd_ppa: Mapped[float | None] = mapped_column(Float)
    tipo_salario: Mapped[str | None] = mapped_column(Text)
    metodo_ppa: Mapped[str | None] = mapped_column(Text)
    es_observado: Mapped[bool] = mapped_column(Boolean, default=True)


class FactInstitucionesEgresados(Base):
    """Tabla de hechos de instituciones universitarias y graduados."""

    __tablename__ = "hecho_instituciones_egresados"
    __table_args__ = (
        Index("ix_hecho_inst_pais_anio", "pais", "anio"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pais: Mapped[str] = mapped_column(String(3))
    fuente_id: Mapped[str] = mapped_column(Text)
    institucion: Mapped[str] = mapped_column(Text)
    tipo_gestion: Mapped[str | None] = mapped_column(Text)
    tipo_institucion: Mapped[str | None] = mapped_column(Text)
    sector: Mapped[str] = mapped_column(Text)
    anio: Mapped[int] = mapped_column(Integer)
    es_observado: Mapped[bool] = mapped_column(Boolean, default=True)
    graduados: Mapped[float] = mapped_column(Float)


class FactOcupacionTerciarios(Base):
    """Tabla de hechos de insercion y ocupacion terciaria."""

    __tablename__ = "hecho_ocupacion_terciarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pais: Mapped[str] = mapped_column(String(3))
    fuente_id: Mapped[str] = mapped_column(Text)
    sector: Mapped[str] = mapped_column(Text)
    anio: Mapped[int] = mapped_column(Integer)
    puestos_empleo: Mapped[float | None] = mapped_column(Float)
    share_mujeres: Mapped[float | None] = mapped_column(Float)
    meses_observados: Mapped[float | None] = mapped_column(Float)
    empleabilidad_1er_anio: Mapped[float | None] = mapped_column(Float)
    empleabilidad_2do_anio: Mapped[float | None] = mapped_column(Float)
    es_observado: Mapped[bool] = mapped_column(Boolean, default=True)


class ReporteDensidadProfesional(Base):
    """Reporte de densidad profesional: graduados por cada 1.000 ocupados."""

    __tablename__ = "reporte_densidad_profesional_sector"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pais: Mapped[str] = mapped_column(String(3))
    sector: Mapped[str] = mapped_column(Text)
    anio: Mapped[int] = mapped_column(Integer)
    graduados_anuales: Mapped[float | None] = mapped_column(Float)
    puestos_empleo: Mapped[float | None] = mapped_column(Float)
    graduados_por_mil_ocupados: Mapped[float | None] = mapped_column(Float)
    ratio_graduados_vs_empleo_pct: Mapped[float | None] = mapped_column(Float)
    fuente_graduados: Mapped[str | None] = mapped_column(Text)
    fuente_empleo: Mapped[str | None] = mapped_column(Text)
    concepto: Mapped[str | None] = mapped_column(Text)


class RankingUniversidadesNacional(Base):
    """Ranking nacional de universidades por volumen de graduados."""

    __tablename__ = "ranking_universidades_nacional"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institucion: Mapped[str] = mapped_column(Text)
    tipo_gestion: Mapped[str | None] = mapped_column(Text)
    graduados: Mapped[float] = mapped_column(Float)
    ranking_nacional: Mapped[int] = mapped_column(Integer)
    tipo_ranking: Mapped[str] = mapped_column(Text)
    pais: Mapped[str] = mapped_column(String(3))
    anio_evaluado: Mapped[str] = mapped_column(Text)
    periodo_tipo: Mapped[str | None] = mapped_column(Text)
    periodo_detalle: Mapped[str | None] = mapped_column(Text)
    total_instituciones_pais: Mapped[int | None] = mapped_column(Integer)
    cobertura: Mapped[str | None] = mapped_column(Text)


class RankingUniversidadesRegional(Base):
    """Ranking regional tripartito de universidades en ventana comun."""

    __tablename__ = "ranking_universidades_regional"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institucion: Mapped[str] = mapped_column(Text)
    pais: Mapped[str] = mapped_column(String(3))
    tipo_gestion: Mapped[str | None] = mapped_column(Text)
    graduados: Mapped[float] = mapped_column(Float)
    ranking_regional: Mapped[int] = mapped_column(Integer)
    anio_evaluado: Mapped[str] = mapped_column(Text)
    criterio_paridad: Mapped[str | None] = mapped_column(Text)
    periodo_tipo: Mapped[str | None] = mapped_column(Text)
    periodo_detalle: Mapped[str | None] = mapped_column(Text)


class AnalisisGeneroIntegral(Base):
    """Analisis integral de genero en educacion superior y mercado laboral."""

    __tablename__ = "analisis_genero_integral"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pais: Mapped[str] = mapped_column(String(3))
    sector: Mapped[str] = mapped_column(Text)
    periodo_graduados: Mapped[str | None] = mapped_column(Text)
    f: Mapped[float | None] = mapped_column(Float)
    m: Mapped[float | None] = mapped_column(Float)
    nb: Mapped[float | None] = mapped_column(Float)
    total_graduados: Mapped[float | None] = mapped_column(Float)
    pct_mujeres_graduadas: Mapped[float | None] = mapped_column(Float)
    pct_varones_graduados: Mapped[float | None] = mapped_column(Float)
    pct_nb_graduados: Mapped[float | None] = mapped_column(Float)
    brecha_graduados_pct: Mapped[float | None] = mapped_column(Float)
    anio_empleo: Mapped[int | None] = mapped_column(Integer)
    pct_mujeres_empleadas: Mapped[float | None] = mapped_column(Float)
    brecha_empleo_pct: Mapped[float | None] = mapped_column(Float)
    diagnostico_paridad: Mapped[str | None] = mapped_column(Text)
    criterio_referencia: Mapped[str | None] = mapped_column(Text)


class ProyeccionesGraduadosSector(Base):
    """Proyecciones de graduados por sector con t-Student e IC 95%."""

    __tablename__ = "proyecciones_graduados_sector"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pais: Mapped[str] = mapped_column(String(3))
    sector: Mapped[str] = mapped_column(Text)
    ultimo_anio_observado: Mapped[int] = mapped_column(Integer)
    ultimo_valor_observado: Mapped[float] = mapped_column(Float)
    horizonte_anios: Mapped[int] = mapped_column(Integer)
    anio_proyectado: Mapped[int] = mapped_column(Integer)
    valor_proyectado: Mapped[float] = mapped_column(Float)
    limite_inferior_95: Mapped[float | None] = mapped_column(Float)
    limite_superior_95: Mapped[float | None] = mapped_column(Float)
    pendiente_anual: Mapped[float | None] = mapped_column(Float)
    r2: Mapped[float | None] = mapped_column(Float)
    n_puntos_base: Mapped[int] = mapped_column(Integer)
    modelo: Mapped[str] = mapped_column(Text)
    advertencia_tendencia: Mapped[str | None] = mapped_column(Text)
