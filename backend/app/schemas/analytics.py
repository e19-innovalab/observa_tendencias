from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


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
    source: str = "LinkedIn (Apify), clasificación por reglas; no es una fuente oficial"


class JobsSummaryCell(BaseModel):
    provincia: str
    sector: str
    n: int


GRADUATES_SOURCE = (
    "SIES (Chile) y datos.gob.ar (Argentina), procesado por el equipo de datos. "
    "Las proyecciones son orientativas."
)


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
    source: str = GRADUATES_SOURCE


class JobsSummary(BaseModel):
    total: int
    scraped_at: datetime | None
    por_provincia_sector: list[JobsSummaryCell]
    source: str = "LinkedIn (Apify), clasificación por reglas; no es una fuente oficial"
