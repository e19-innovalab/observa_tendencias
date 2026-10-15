# Observatorio predictivo de tendencias: Plan de Backend (Prototipo MVP)

> Alcance: Argentina, Uruguay, Chile · 5 sectores (Tecnología, Salud, Energía, Turismo, Economía del conocimiento) · ~20 ocupaciones
> Stack: Python + FastAPI · PostgreSQL (Supabase) · Pandas / NumPy · HTTPX · Statsmodels / Scikit-learn · APScheduler / Cron · Render o Railway
> Convención: los nombres de variables, funciones, tablas y endpoints están en inglés.

---

## 1. Objetivos del backend para el prototipo

El backend debe hacer funcionar de punta a punta este flujo mínimo:

```
consumir fuente oficial → actualizar datos → normalizar → calcular indicadores
→ exponer vía API → consultar tendencia o brecha → identificar fuente y fecha
```

El diseño sigue cuatro principios:

1. **Los conectores son plugins independientes.** Sumar un país o una fuente implica agregar un conector, no reconstruir la plataforma (brief, sección 6).
2. **Los datos crudos nunca se sobrescriben.** Cada ingesta se guarda tal como llegó y la normalización se aplica encima. Esto permite reprocesar y auditar.
3. **Cada valor conserva su origen.** Cada fila registra fuente, corrida de ingesta, fecha de obtención y tipo de dato (`observed`, `calculated`, `projected`).
4. **Las metodologías son datos versionados, no lógica fija en el código.** Ponderaciones del índice, umbrales de tendencia y reglas de alertas viven en tablas, así se pueden ajustar en la Semana 9 sin redeployar.

---

## 2. Arquitectura general

```
┌──────────────────────────────────────────────────────────────────┐
│                          FUENTES                                 │
│  APIs: World Bank · ILOSTAT · CEPALSTAT · Datos Argentina ·      │
│        SIMEL (INE Chile) · Banco Central de Chile                │
│  Datasets: INDEC EPH · INE Uruguay ECH · SABE · SIES · ANEP ...  │
│  Carga manual: CSV / XLSX / JSON                                 │
└───────────────┬──────────────────────────────────────────────────┘
                │
        ┌───────▼────────┐
        │  1. INGESTA    │  connectors/ + uploads/
        │  (capa cruda)  │  → raw_records, ingestion_runs
        └───────┬────────┘
        ┌───────▼────────┐
        │ 2. NORMALIZAR  │  crosswalks (ISO3, CIIU/ISIC, CIUO/ISCO),
        │ (canónica)     │  períodos, unidades, moneda → observations
        └───────┬────────┘
        ┌───────▼────────┐
        │ 3. ANÁLISIS    │  índice de empleabilidad · tendencias ·
        │ (calculado)    │  proyecciones · brechas · alertas
        └───────┬────────┘
        ┌───────▼────────┐
        │ 4. API (REST)  │  FastAPI → dashboard Next.js
        └────────────────┘
                ▲
        ┌───────┴────────┐
        │  SCHEDULER     │  jobs por fuente → ingesta → normalización
        │                │  → recálculo de indicadores afectados
        └────────────────┘
```

---

## 3. Estructura del proyecto

```
backend/
├── app/
│   ├── main.py                    # App FastAPI, registro de routers
│   ├── core/
│   │   ├── config.py              # Settings (pydantic-settings, variables de entorno)
│   │   ├── database.py            # Engine / sesión SQLAlchemy
│   │   └── logging.py
│   ├── models/                    # Modelos ORM SQLAlchemy
│   ├── schemas/                   # Schemas Pydantic de request/response
│   ├── api/
│   │   └── v1/
│   │       ├── catalog.py         # países, sectores, ocupaciones
│   │       ├── indicators.py
│   │       ├── employability.py
│   │       ├── trends.py
│   │       ├── skills.py
│   │       ├── alerts.py
│   │       ├── datasets.py        # carga manual
│   │       └── sources.py         # fuentes, historial, estado
│   ├── connectors/
│   │   ├── base.py                # BaseConnector
│   │   ├── registry.py            # registro de conectores
│   │   ├── world_bank.py
│   │   ├── ilostat.py
│   │   ├── cepalstat.py
│   │   ├── datos_argentina.py
│   │   ├── simel_chile.py
│   │   └── bcentral_chile.py
│   ├── ingestion/
│   │   ├── pipeline.py            # run_ingestion(source_code)
│   │   └── uploads.py             # validate_upload, commit_upload
│   ├── normalization/
│   │   ├── crosswalks.py          # map_country, map_sector, map_occupation
│   │   ├── periods.py             # parse_period, to_period_range
│   │   ├── units.py               # normalize_unit, convert_currency
│   │   └── normalizer.py          # normalize_run(run_id)
│   ├── analytics/
│   │   ├── employability.py       # compute_employability_index
│   │   ├── trends.py              # classify_trend, compute_growth
│   │   ├── projections.py         # project_series
│   │   ├── skill_gaps.py          # compute_skill_gaps
│   │   └── alerts.py              # evaluate_alert_rules
│   ├── jobs/
│   │   └── scheduler.py           # jobs APScheduler
│   └── services/                  # lógica de consulta usada por la API
├── migrations/                    # Alembic
├── seeds/                         # catálogo, crosswalks, metodología v1
├── tests/
│   ├── fixtures/                  # respuestas de APIs grabadas
│   ├── test_connectors.py
│   ├── test_normalization.py
│   ├── test_analytics.py
│   └── test_api.py
├── pyproject.toml
└── Dockerfile
```

---

## 4. Modelo de datos

### 4.1 Tablas de catálogo

| Tabla | Columnas clave | Notas |
|---|---|---|
| `countries` | `iso3`, `name_es`, `name_en` | ARG, URY, CHL |
| `sectors` | `sector_code`, `name`, `isic_codes[]` | Cada sector del MVP se mapea a una lista de códigos CIIU/ISIC Rev.4 |
| `occupations` | `occupation_code`, `name`, `isco08_code`, `sector_code` | ~20 filas; CIUO-08/ISCO-08 es la clave común |
| `occupation_crosswalks` | `country_iso3`, `national_code`, `national_system`, `isco08_code` | ej. CNO-2001 de Argentina → ISCO-08 |
| `skills` | `skill_code`, `name`, `skill_type`, `esco_uri` | ESCO como taxonomía de referencia opcional |
| `occupation_skills` | `occupation_code`, `skill_code`, `country_iso3`, `weight`, `source_id` | |

### 4.2 Tablas de fuentes e ingesta

| Tabla | Columnas clave | Notas |
|---|---|---|
| `sources` | `source_code`, `name`, `source_kind` (`api` / `dataset` / `manual`), `base_url`, `expected_frequency`, `is_active` | |
| `ingestion_runs` | `run_id`, `source_id`, `started_at`, `finished_at`, `status`, `records_fetched`, `records_normalized`, `error_message`, `triggered_by` (`scheduler` / `manual` / `upload`) | Es el historial de actualizaciones |
| `raw_records` | `raw_id`, `run_id`, `payload` (JSONB), `source_series_id` | Datos de la fuente sin modificar |
| `uploaded_datasets` | `dataset_id`, `run_id`, `file_name`, `file_hash`, `country_iso3`, `declared_source`, `reference_date`, `status`, `replaces_dataset_id` | Permite actualizar o reemplazar |

### 4.3 Tablas de indicadores (el núcleo)

| Tabla | Columnas clave | Notas |
|---|---|---|
| `indicators` | `indicator_code`, `name`, `unit`, `description`, `domain` (`labor` / `economic` / `education`), `higher_is_better` | Definiciones |
| `observations` | ver DDL abajo | Única tabla de hechos |

```sql
CREATE TYPE data_type AS ENUM ('observed', 'calculated', 'projected');

CREATE TABLE observations (
    observation_id    BIGSERIAL PRIMARY KEY,
    indicator_code    TEXT NOT NULL REFERENCES indicators(indicator_code),
    country_iso3      CHAR(3) NOT NULL REFERENCES countries(iso3),
    sector_code       TEXT NULL REFERENCES sectors(sector_code),
    occupation_code   TEXT NULL REFERENCES occupations(occupation_code),
    period_start      DATE NOT NULL,
    period_end        DATE NOT NULL,
    frequency         TEXT NOT NULL,           -- 'A', 'Q', 'M'
    value             NUMERIC NOT NULL,
    unit              TEXT NOT NULL,
    data_type         data_type NOT NULL,
    source_id         INT NOT NULL REFERENCES sources(source_id),
    run_id            INT NULL REFERENCES ingestion_runs(run_id),
    methodology_id    INT NULL,                -- para calculated / projected
    lower_bound       NUMERIC NULL,            -- solo proyecciones
    upper_bound       NUMERIC NULL,
    source_updated_at TIMESTAMPTZ NULL,        -- fecha declarada por la fuente
    fetched_at        TIMESTAMPTZ NOT NULL,
    UNIQUE (indicator_code, country_iso3, sector_code, occupation_code,
            period_start, frequency, data_type, source_id)
);
```

La clave única hace que la ingesta sea **idempotente**: volver a correr un conector actualiza (upsert) en lugar de duplicar.

### 4.4 Tablas de análisis

| Tabla | Columnas clave |
|---|---|
| `methodologies` | `methodology_id`, `methodology_type` (`employability_index` / `trend` / `projection` / `alert`), `version`, `params` (JSONB), `description_md`, `is_active`, `created_at` |
| `employability_scores` | `country_iso3`, `occupation_code`, `period_start`, `score`, `level`, `components` (JSONB), `methodology_id`, `computed_at`, `coverage_ratio` |
| `trend_results` | `indicator_code`, `country_iso3`, `sector_code`, `occupation_code`, `window`, `slope`, `pct_change`, `trend_state` (`growing` / `stable` / `declining`), `methodology_id`, `computed_at` |
| `skill_gaps` | `country_iso3`, `occupation_code`, `skill_code`, `demand_score`, `supply_score`, `gap_score`, `is_emerging`, `data_sufficiency`, `computed_at` |
| `alerts` | `alert_id`, `alert_type`, `severity`, `entity_type`, `entity_code`, `country_iso3`, `message`, `previous_value`, `current_value`, `rule_id`, `detected_at`, `is_read` |

---

## 5. Conectores

### 5.1 Interfaz común

```python
class BaseConnector(ABC):
    source_code: str

    @abstractmethod
    async def fetch(self, series_ids: list[str], since: date | None) -> list[dict]:
        """Call the external source and return raw payloads."""

    @abstractmethod
    def to_canonical(self, raw_payload: dict) -> list[CanonicalRecord]:
        """Map one raw payload to canonical records (not yet saved)."""

    async def health_check(self) -> SourceHealth:
        """Lightweight request to check availability."""
```

`CanonicalRecord` es un modelo Pydantic con `indicator_code`, `country_iso3`, `sector_code`, `occupation_code`, `period`, `value`, `unit`, `source_updated_at`.

Cada conector lee su **mapeo de series** desde un archivo de configuración (`seeds/series_map.yaml`) que vincula los IDs de series de la fuente con los `indicator_code` internos. Agregar una serie no requiere cambiar código.

### 5.2 Prioridad de conectores

| Prioridad | Conector | Países | Por qué |
|---|---|---|---|
| P0 (Semana 1) | `WorldBankConnector` | ARG, URY, CHL | REST JSON simple, sin autenticación, mismos códigos para los tres países. Buena primera prueba de punta a punta. |
| P0 (Semana 1) | `IlostatConnector` | ARG, URY, CHL | Empleo y salarios por ocupación (ISCO) y sector (ISIC). Principal fuente comparable. Usa SDMX. |
| P1 (Semanas 2–3) | `DatosArgentinaConnector` | ARG | API de Series de Tiempo, actualización diaria. |
| P1 (Semanas 2–3) | `SimelChileConnector` | CHL | Datos laborales nacionales, salida JSON/CSV. |
| P2 (Semanas 3–4) | `CepalstatConnector` | ARG, URY, CHL | Contexto socioeconómico regional. |
| P2 (opcional) | `BcentralChileConnector` | CHL | Requiere registrarse para obtener credenciales; guardarlas en variables de entorno, nunca en el código. |

> **Tarea de la Semana 1:** confirmar cada endpoint, requisitos de autenticación, límites de uso y formatos de respuesta contra la documentación oficial, y guardar una respuesta de ejemplo por fuente en `tests/fixtures/`.

### 5.3 Datasets complementarios (descarga programada)

Las fuentes sin API (INDEC EPH, ECH de INE Uruguay, SABE, SIES, ANEP) pasan por un `DatasetDownloadConnector` que descarga un archivo desde una URL conocida de forma programada y lo procesa con la misma validación de la carga manual. Si la URL cambia o la descarga falla, la fuente se marca como `unavailable` en lugar de romper el pipeline.

---

## 6. Carga manual de datasets

Flujo en dos pasos, para que el usuario revise la vista previa antes de confirmar:

```
POST /api/v1/datasets/upload     → valida, devuelve preview + errores (status: 'pending')
POST /api/v1/datasets/{id}/commit → normaliza y escribe en observations
POST /api/v1/datasets/{id}/replace?replaces={old_id} → reemplaza un dataset anterior
```

**Validaciones (`validate_upload`)**

- Formatos permitidos: CSV, XLSX, JSON; tamaño máximo (ej. 20 MB).
- Columnas obligatorias: `indicator_code`, `country_iso3`, `period`, `value`, `unit`. Opcionales: `sector_code`, `occupation_code`.
- Metadatos obligatorios en la request: `declared_source`, `reference_date`, `country_iso3`.
- Tipos: `value` numérico; `period` interpretable (`2024`, `2024-Q3`, `2024-07`).
- Validación contra catálogo: los códigos existen en `indicators`, `countries`, `sectors`, `occupations`.
- Detección de archivo duplicado por `file_hash`.
- Resultado: lista de errores por fila (`row`, `column`, `error`), no un único error genérico.

Implementación: Pandas + OpenPyXL para leer, Pandera o Pydantic para validar el esquema.

---

## 7. Normalización

`normalize_run(run_id)` toma los registros crudos de una corrida y genera filas en `observations`.

| Problema | Solución |
|---|---|
| Códigos de país distintos | `map_country()` → ISO3 |
| Clasificaciones de ocupación distintas | `map_occupation()` vía `occupation_crosswalks` → ISCO-08 → `occupation_code` interno |
| Sectores | `map_sector()` vía listas CIIU/ISIC Rev.4 en `sectors.isic_codes` |
| Frecuencias mezcladas | `to_period_range()` → `period_start`, `period_end`, `frequency`. No se remuestrea al guardar; la agregación se hace al consultar. |
| Salarios en moneda local | Se conserva el valor original. Las comparaciones entre países usan indicadores derivados (variación % del salario real, o USD PPA cuando haya factor de conversión), guardados como `calculated`. |
| Porcentajes vs. tasas | `normalize_unit()` → unidades consistentes (`percent`, `persons`, `local_currency`, `index`) |
| Registros que no se pueden mapear | Se guardan en `normalization_issues` (run_id, raw_id, motivo) y se reportan, no se descartan en silencio |

> **Decisión pendiente (Semana 0):** "Economía del conocimiento" y "Tecnología" no son secciones de CIIU/ISIC y se superponen. Definir explícitamente qué divisiones ISIC corresponden a cada uno (por ejemplo, J62–63 para Tecnología; M69–75 más J62–63 para Economía del conocimiento) y documentarlo en la metodología.

---

## 8. Análisis

Todas las funciones de análisis leen sus parámetros de la fila activa en `methodologies` y registran el `methodology_id` en sus resultados.

### 8.1 Índice de Empleabilidad (`compute_employability_index`)

Dimensiones propuestas para la v1 (a confirmar con el equipo de Data según disponibilidad real):

| Dimensión | Variable de ejemplo | Dirección |
|---|---|---|
| `demand` | Crecimiento interanual del empleo de la ocupación | más alto es mejor |
| `wages` | Crecimiento del salario real | más alto es mejor |
| `stability` | Tasa de informalidad o desempleo del sector | más bajo es mejor |
| `outlook` | Pendiente de la tendencia en los últimos N períodos | más alto es mejor |
| `skills_fit` | Inverso de la brecha promedio de habilidades (opcional en v1) | más alto es mejor |

Cálculo:

1. Para cada variable, normalización min-max a 0–100 dentro de la cohorte de comparación (todas las ocupaciones del mismo país y período), invirtiendo cuando `higher_is_better = false`.
2. Suma ponderada con `params.weights` (ejemplo v1: 0,30 / 0,25 / 0,20 / 0,15 / 0,10).
3. Si falta una dimensión, se redistribuye su peso entre las disponibles y se registra `coverage_ratio`. Por debajo de un umbral (ej. 0,6), se devuelve `level = "insufficient_data"` en lugar de un puntaje.
4. Niveles: `low` (<40), `medium` (40–70), `high` (>70), configurables en `params.levels`.
5. Se guarda `components` con el valor crudo, el valor normalizado y el peso de cada dimensión, para que el dashboard pueda explicar el puntaje.

> Nota: el min-max dentro de una cohorte hace que el puntaje sea **relativo** (comparado con otras ocupaciones del mismo país). Las comparaciones entre países deben presentarse con esa aclaración, o usar límites de referencia fijos definidos en la metodología.

### 8.2 Tendencias (`classify_trend`)

- Entradas: serie, `window` (ej. últimos 8 trimestres o 5 años).
- Se calcula `pct_change` en la ventana y la pendiente de una regresión lineal sobre la serie.
- Clasificación: `growing` si la pendiente normalizada > `+threshold`, `declining` si < `-threshold`, si no `stable`. Umbral por defecto en `params` (ej. ±2% anual).
- Se exige una cantidad mínima de puntos; si no, `trend_state = "insufficient_data"`.

### 8.3 Proyecciones (`project_series`)

- Modelo: Exponential Smoothing (Holt) de Statsmodels para el MVP. Simple, robusto con series cortas y entrega intervalos de confianza.
- Horizonte corto (1–4 períodos), guardado con `data_type = 'projected'` más `lower_bound` y `upper_bound`.
- Solo se genera cuando la serie tiene historia suficiente (ej. ≥ 12 puntos).
- Siempre se marca como orientativa en la respuesta de la API.

### 8.4 Brechas de habilidades (`compute_skill_gaps`)

- **Lado demanda:** habilidades asociadas a cada ocupación (mapeo de referencia ESCO/O*NET, enriquecido con SABE para Chile cuando esté disponible).
- **Lado oferta:** matrícula y egresados por campo de estudio (SIES, ANEP, datos abiertos de Educación de Argentina), vinculados a ocupaciones mediante una tabla `field_occupation_map` (campo CINE-F/ISCED-F → ocupaciones).
- `gap_score = demand_score - supply_score` (ambos normalizados 0–100).
- `is_emerging = true` cuando el crecimiento de la demanda de la habilidad supera un umbral (requiere datos de demanda en el tiempo; en el MVP, realistamente solo Chile).
- `data_sufficiency`: `full`, `partial`, `none`. El brief dice "cuando existan datos suficientes", así que la API debe devolver `none` explícitamente en lugar de inventar una brecha.

### 8.5 Alertas (`evaluate_alert_rules`)

Reglas guardadas en `methodologies` (`methodology_type = 'alert'`). Reglas del MVP:

| `alert_type` | Condición |
|---|---|
| `significant_change` | Variación absoluta entre períodos > X% o z-score > 2 respecto del histórico |
| `index_level_change` | Cambió el nivel de empleabilidad (ej. `medium` → `high`) |
| `trend_reversal` | `trend_state` distinto al del cálculo anterior |
| `new_skill_gap` | Un `gap_score` superó el umbral por primera vez |
| `stale_source` | Fuente sin actualizar dentro de `expected_frequency × 1.5` |

El MVP exige al menos un tipo de alerta. `significant_change` es el mínimo; el resto es incremental.

---

## 9. Endpoints de la API (v1)

| Método | Ruta | Propósito |
|---|---|---|
| GET | `/api/v1/countries` · `/sectors` · `/occupations` | Catálogos para filtros |
| GET | `/api/v1/indicators` | Definiciones de indicadores |
| GET | `/api/v1/observations?indicator=&country=&sector=&occupation=&from=&to=&data_type=` | Series temporales con fuente y fecha en cada punto |
| GET | `/api/v1/dashboard/summary?country=` | Cifras clave para el dashboard principal |
| GET | `/api/v1/compare?indicator=&countries=ARG,URY,CHL&occupation=` | Comparación entre países |
| GET | `/api/v1/employability?country=&occupation=&period=` | Puntaje, nivel, componentes |
| GET | `/api/v1/employability/history?country=&occupation=` | Evolución del índice |
| GET | `/api/v1/trends?country=&sector=&occupation=` | Estados de tendencia |
| GET | `/api/v1/projections?indicator=&country=&occupation=` | Puntos proyectados con intervalos |
| GET | `/api/v1/skills/gaps?country=&occupation=` | Brechas y habilidades emergentes |
| GET | `/api/v1/alerts?country=&severity=&unread=` · PATCH `/alerts/{id}/read` | Panel de alertas |
| POST | `/api/v1/datasets/upload` · `/{id}/commit` · `/{id}/replace` | Carga manual |
| GET | `/api/v1/sources` · `/sources/{code}/runs` | Historial de actualizaciones, estado de fuentes |
| POST | `/api/v1/sources/{code}/refresh` | Disparo manual de actualización (admin) |
| GET | `/api/v1/methodologies/{type}` | Texto y parámetros de la metodología |
| GET | `/health` | Estado del servicio |

**Convención de respuesta para trazabilidad:** cada dato que devuelve la API incluye:

```json
{
  "value": 7.4,
  "unit": "percent",
  "period": "2025-Q2",
  "data_type": "observed",
  "source": { "code": "ilostat", "name": "ILOSTAT" },
  "source_updated_at": "2025-09-12",
  "fetched_at": "2026-09-20T03:00:00Z",
  "methodology_id": null
}
```

FastAPI genera la especificación OpenAPI automáticamente; QA puede importarla en Postman.

Autenticación: en el MVP los endpoints de lectura pueden quedar abiertos, con una API key simple (header `X-API-Key`) en los endpoints de carga, refresh y marcado de alertas.

---

## 10. Programación y actualización automática

- **Prototipo:** APScheduler dentro del proceso de FastAPI (simple). **Deploy:** cron job de Render/Railway que ejecuta `python -m app.jobs.run --source=<code>` (más confiable si el servicio web se suspende).
- Un job por fuente, con frecuencia según `sources.expected_frequency` (ej. Datos Argentina diario, ILOSTAT/World Bank chequeo semanal).
- Cadena del job: `run_ingestion(source)` → `normalize_run(run_id)` → `recompute_affected(run_id)` → `evaluate_alert_rules()`.
- `recompute_affected` solo recalcula los indicadores cuyos insumos cambiaron (según país/ocupación/indicador tocados en la corrida).
- Reintentos con backoff ante errores de red; después de N fallos, la corrida queda `failed` y la fuente se marca `unavailable`. El dashboard sigue mostrando el último dato válido con estado "desactualizado".

---

## 11. Testing y calidad

- **Tests unitarios (pytest):** funciones de normalización, crosswalks, cálculo del índice con entradas y salidas conocidas, casos borde de clasificación de tendencias.
- **Tests de conectores:** usan respuestas grabadas en `tests/fixtures/` (sin llamadas reales en CI). Un smoke test real opcional por conector, ejecutado manualmente.
- **Tests de API:** `TestClient` de FastAPI contra una base de test con datos sembrados.
- **Controles de calidad de datos después de cada corrida:** cantidad de filas vs. corrida anterior, nulos, valores fuera de rango (ej. desempleo > 100%).
- CI: GitHub Actions con lint (ruff) y tests en cada PR.

---

## 12. Entregables de backend por semana

| Semana | Entregables de backend |
|---|---|
| 0 | Repo, esqueleto FastAPI, base Supabase, Alembic, tablas y seeds de catálogo, configuración `.env` |
| 1 | `BaseConnector`, `WorldBankConnector` e `IlostatConnector` obteniendo y guardando datos crudos; `ingestion_runs` |
| 2 | Tabla `observations`, primer `normalize_run`, primer endpoint `/observations`, carga manual básica (solo validación) |
| 3 | Endpoints de catálogo y dashboard, commit de carga manual, conectores Datos Argentina + SIMEL |
| 4 | Tabla `methodologies`, `compute_employability_index`, endpoints `/employability`, historial guardado |
| 5 | `classify_trend`, `trend_results`, `/trends`, `/compare`, endpoints de series históricas |
| 6 | Tablas de habilidades, `field_occupation_map`, `compute_skill_gaps`, `/skills/gaps` |
| 7 | Tabla `alerts`, `evaluate_alert_rules`, `/alerts` |
| 8 | Scheduler, `recompute_affected`, detección de `stale_source`, historial en `/sources`, reemplazo de datasets |
| 9 | Optimización de consultas (índices en `observations`), manejo de errores, `project_series` + `/projections` |
| 10 | Estabilidad de conectores y jobs; manejo de fuentes no disponibles |
| 11 | Validación de punta a punta con QA, corrección de bugs críticos |
| 12 | Entorno estable para la demo, snapshot de datos precargado como respaldo, documentación metodológica |

---

## 13. Riesgos y decisiones abiertas

| Riesgo / decisión | Mitigación |
|---|---|
| Pocos datos a nivel ocupación, sobre todo en Uruguay | Usar ILOSTAT (ISCO) como base; aceptar indicadores sectoriales como proxy y marcarlos explícitamente |
| Las fuentes cambian URLs o formatos | Conectores aislados, fixtures, alertas `stale_source`, conservar el último dato válido |
| Mapeo de "Economía del conocimiento" y "Tecnología" a ISIC | Decidir en la Semana 0 y documentar |
| El índice parece preciso pero mezcla datos desparejos | `coverage_ratio`, nivel `insufficient_data`, metodología publicada |
| Datos de habilidades sólidos solo para Chile | Informar `data_sufficiency` por país; no inventar brechas |
| APIs externas caídas durante el Demo Day | Mantener un snapshot de la base y un modo demo que lea solo de la base local |
| Moneda e inflación (sobre todo Argentina) | Comparar tasas de crecimiento y variaciones reales, no niveles nominales entre países |
