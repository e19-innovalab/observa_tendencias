from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.core.config_files import JobsView, app_config

NOTICES = app_config().notices


class CoverageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pais: str
    sector: str
    n_anios_observados: int
    anio_min: int | None
    anio_max: int | None
    elegible_proyeccion: bool
    estado: str


class JobItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pais: str
    provincia: str
    sector: str
    regla_clasificacion: str
    titulo: str
    empresa: str | None
    ubicacion: str | None
    fecha_publicacion: date | None
    nivel_experiencia: str | None
    tipo_empleo: str | None
    industria: str | None
    postulantes: int | None
    url: str
    scraped_at: datetime


class JobsPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[JobItem]
    source: str = NOTICES["jobs"]


class JobsSummaryCell(BaseModel):
    provincia: str
    sector: str
    n: int


class GraduateTrendItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pais: str
    nombre: str
    anio_desde: int
    anio_hasta: int
    n_anios_serie: int
    ventana_anios: int
    graduados_inicio_ventana: int
    graduados_ultimo: int
    variacion_ventana_pct: float | None
    tendencia: str
    tiene_huecos: bool
    proyeccion: str


class GraduateProjectionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pais: str
    nombre: str
    anio: int
    graduados_proyectado: int
    limite_inferior: int
    limite_superior: int


class GraduateTrends(BaseModel):
    items: list[GraduateTrendItem]
    source: str = NOTICES["graduates"]


class JobsSummary(BaseModel):
    total: int
    scraped_at: datetime | None
    por_provincia_sector: list[JobsSummaryCell]
    source: str = NOTICES["jobs"]
    # how to show it (app.yaml -> jobs_view): notice, sector order with "other" last, page size
    view: JobsView = app_config().jobs_view


class DensidadProfesionalItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pais: str
    sector: str
    anio: int
    graduados_anuales: float | None = None
    puestos_empleo: float | None = None
    graduados_por_mil_ocupados: float | None = None
    ratio_graduados_vs_empleo_pct: float | None = None
    fuente_graduados: str | None = None
    fuente_empleo: str | None = None
    concepto: str | None = None


class DensidadProfesionalResponse(BaseModel):
    total: int
    enfoque: str
    ventana_temporal: str
    nota_metodologica: str
    items: list[DensidadProfesionalItem]


class SalarioDualItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pais: str
    sector: str
    anio: int
    fuente_id: str
    carrera_objetivo: str | None = None
    salario_moneda_local: float | None = None
    moneda_local: str | None = None
    factor_ppa: float | None = None
    salario_usd_ppa: float | None = None
    tipo_salario: str | None = None
    metodo_ppa: str | None = None
    es_observado: bool = True


class SalarioDualResponse(BaseModel):
    total: int
    enfoque: str
    nota_metodologica: str
    items: list[SalarioDualItem]


class ISEMetodologiaInsercionResponse(BaseModel):
    metodologia: str
    version: str
    tratamiento_insercion: str
    justificacion_metodologica: str
    pesos_nominales: dict[str, float]
    pesos_efectivos_redistribuidos: dict[str, float]
    disponibilidad_por_pais: dict[str, str]


class MatrizHabilidadIAItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    carrera_id: str
    carrera_objetivo: str
    sector: str
    cine_f_codigo: str
    nivel_esperado: str
    ciuo_08: str
    ocupacion_nombre_es: str
    ocupacion_nombre_en: str
    oit_exposicion_media: float
    oit_desvio_std: float
    oit_gradiente: str
    tipologia_habilidad: str
    vector_emergencia: str | None = None
    habilidades_nucleares: str | None = None
    habilidades_emergentes_sector: str | None = None
    habilidades_transversales_humanas: str | None = None
    habilidades_digitales_ia: str | None = None
    impacto_ia_resumen: str
    habilidades_clave_esco: str
    demanda_observada_linkedin: str
    recomendacion_curricular: str
    fuente_mapeo: str
    fuente_ofertas: str



class MatrizHabilidadIAResponse(BaseModel):
    total: int
    sector_filtro: str | None = None
    tipologia_filtro: str | None = None
    resumen_por_sector: dict[str, int]
    resumen_por_tipologia: dict[str, int]
    nota_metodologica: str
    items: list[MatrizHabilidadIAItem]


