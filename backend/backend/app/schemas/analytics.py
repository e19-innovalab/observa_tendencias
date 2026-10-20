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
