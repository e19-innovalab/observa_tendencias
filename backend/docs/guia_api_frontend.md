# Guía de la API para el frontend

Qué endpoint alimenta cada pantalla del mockup ("Wireframes Observatorio Innova Lab" en Figma),
qué devuelve y qué convenciones seguir. Estado al 18/10/2026.

- **Base URL (local):** `http://localhost:8010/api/v1`. La URL de despliegue se define más adelante, junto con Supabase.
- **Documentación interactiva** (todos los parámetros y esquemas): http://localhost:8010/docs. Se puede importar en Postman desde `http://localhost:8010/openapi.json`.
- **Implementación de referencia:** el Explorer (http://localhost:8010/explorer, código en `backend/backend/app/static/explorer.html`) usa todos estos endpoints. Si hay dudas de cómo llamar a uno, está ahí.
- **CORS:** los orígenes permitidos se configuran en `backend/.env` (`CORS_ORIGINS`). Para el frontend local, permite `http://localhost:3010`.

---

## 1. Convenciones

### Textos: siempre desde la API

Etiquetas, nombres y mensajes llegan listos en español: `domain_label`, `data_type_label`,
`trend_state_label`, `level_label`, `severity_label`, `message`, entre otros. **No los escriban en
el frontend.** Si cambia un texto, se cambia en la configuración del backend y la interfaz lo toma
sola.

### Países, períodos y filtros

- **País:** siempre `country`, con código ISO3 (`ARG`, `URY`, `CHL`). En los endpoints de datos se aceptan varios separados por coma: `country=ARG,CHL`. La lista sale de `GET /countries`. Los endpoints anteriores (`/jobs`, `/coverage`, `/graduates/trends` y `/graduates/projections`) aceptan `country` y también `pais`, por compatibilidad.
- **Período:** cada valor trae `period` (texto para mostrar: `2025`, `2026-Q2`, `2026-08`), `period_start`, `period_end` y `frequency` (`A` anual, `Q` trimestral, `M` mensual).
- **Rango de años** (filtro "Período" del mockup): `from_year` y `to_year`.
- **Ocupaciones:** se identifican por su código CIUO-08 de 4 dígitos, como `2512`. Ver [`data/scripts/referencias/README.md`](../data/scripts/referencias/README.md) para cómo leerlo.

### Cada valor dice de dónde sale (trazabilidad)

Todos los valores numéricos llegan como un **punto** con fuente y fechas. Así se arma el pie
"Actualización · Ver fuente y metodología" del mockup:

```json
{
  "period": "2025", "value": 7.377, "unit": "percent",
  "data_type": "observed", "data_type_label": "Dato observado",
  "source": { "code": "ilostat", "name": "ILOSTAT" },
  "source_updated_at": null,
  "fetched_at": "2026-10-18T04:05:38Z",
  "methodology_id": null,
  "lower_bound": null, "upper_bound": null
}
```

- **`data_type`:** `observed` (dato de la fuente), `calculated` (lo calcula la plataforma) o `projected` (proyección). El brief exige que la interfaz los distinga visualmente.
- **"Actualización":** mostrar `source_updated_at`, la fecha que informa la fuente. Si viene vacía, usar `fetched_at`, que es cuándo se descargó.
- **"Ver metodología":** si hay `methodology_id`, el texto y los parámetros están en `GET /methodologies/{tipo}`, con tipo `trend`, `projection`, `employability_index`, `skill_gap` o `alert`. Usar `description_md`, un párrafo por línea.

### Unidades

| `unit` | Cómo mostrarla |
|---|---|
| `percent` | `7,4 %`. Los cambios de un porcentaje se expresan en puntos (`change_kind: "absolute"`) |
| `thousands_persons` | Miles de personas (`9.274` = 9,27 millones) |
| `ppp_usd_month` | USD PPA por mes |
| `ppp_usd` | USD PPA |
| `index_0_1` | Índice de 0 a 1, con 2 decimales |

Los crecimientos (`demand_growth`, `supply_growth`, `pct_change` y la dimensión `net_demand`) son
**fracciones**: `0.052` = +5,2 % anual. La brecha (`gap`) también es una fracción, y se muestra en
puntos porcentuales: `0.03` = +3 pp.

### Listados: rankings y páginas

Los listados grandes usan los mismos parámetros:

| Parámetro | Valores |
|---|---|
| `view` | `top` (mejores o mayores), `bottom` (peores o menores), `all` (todo, paginado) |
| `sort_by`, `order` | `asc` o `desc` |
| `limit`, `offset` | Paginación. El tamaño de los rankings (20) viene de la configuración |

La respuesta trae `total` para armar la paginación.

### Errores

- `404` (no existe): `{"detail": "Indicador desconocido: xyz"}`.
- `422`: parámetro inválido.
- `401`: falta la API key en un endpoint de administración.
- `503`: la base de datos no responde.

El texto de `detail` se puede mostrar tal cual.

### Endpoints de administración

`POST` y `PATCH` (actualizar fuentes, cargar archivos, marcar alertas) requieren el header
`X-API-Key`. Todavía no hay usuarios ni login: el login y el rol "Administración" del mockup quedan
pendientes de autenticación.

---

## 2. Pantalla por pantalla

### Menú superior: campana de alertas

- `GET /alerts?unread=true&limit=5`: el número del globo es `unread`, y los ítems son las últimas alertas.
- Ver más abajo "Alertas".

### Inicio

| Elemento | Endpoint | Campos |
|---|---|---|
| Tarjetas (desocupación, actividad, etc.) | `GET /dashboard/summary?country=ARG` | `highlights[]`: `indicator.name`, `current.value`, `current.period`, `change` y `change_kind`. Qué indicadores aparecen se define en la configuración (`app.yaml → dashboard.highlights`) |
| "Últimas tendencias" | `GET /alerts?country=ARG&limit=5` | `message`, `country_iso3`, `indicator.name` o `occupation.name`, `detected_at` (para "hace 2 días") |
| Accesos rápidos | — | Estáticos |

### Panorama regional

| Elemento | Endpoint | Notas |
|---|---|---|
| Pestañas Socioeconómicos, Laborales y Educativos | `GET /indicators?domain=economic\|labor\|education` | El nombre de la pestaña viene en `domain_label` |
| Filtro País | `GET /countries` | |
| Filtro Sector | `GET /sectors` | Solo los indicadores con `has_sector_breakdown: true` aceptan `sector` |
| Lista lateral de indicadores | La misma de las pestañas | `name` y `description` |
| Tarjetas (cifras clave) | `GET /compare?indicator=...` o `/dashboard/summary` | |
| Gráfico de barras "Año actual vs. año pasado" por país | `GET /compare?indicator=gdp_growth&countries=ARG,URY,CHL&sector=` | `items[]`: `country_iso3`, `current`, `previous` y `change` |
| Gráfico de líneas | `GET /observations?indicator=inflation&country=ARG,CHL&from_year=2015` | `items[]` son puntos, uno por país y período |
| Pie "Actualización · Ver fuente y metodología" | Campos del punto | Ver "Trazabilidad" |

### Tendencias y proyecciones

| Elemento | Endpoint | Notas |
|---|---|---|
| Pestaña Tendencias | `GET /trends?indicator=...&country=...&from_year=&to_year=` | `trend_state_label` (Crecimiento, Estabilidad o Disminución) y `assessment_label` (Favorable, Desfavorable o Neutral, según si al indicador le conviene subir). Sin período: la última ventana guardada (`window_mode: "latest"`), con `previous_trend_state`. Con período: calculada para esos años (`window_mode: "range"`) |
| Lista de indicadores por grupo | `GET /trends?domain=labor&country=ARG` | Todas las tendencias de un dominio |
| Pestaña Proyecciones, gráfico "Tendencia actual / Proyección" | `GET /projections?indicator=...&country=...&from_year=` | `items[].observed` (línea continua) y `items[].projected` (línea punteada; `lower_bound` y `upper_bound` para la banda) |
| Recuadro "Fuente, Actualización, Ver metodología" | `GET /methodologies/trend` o `/methodologies/projection` | `description_md` y `params` |

### Ocupaciones

Esta pantalla no tiene diseño en el mockup todavía. Esto es lo que ofrece la API:

| Elemento | Endpoint | Notas |
|---|---|---|
| Buscador y lista | `GET /occupations?featured=true` o `GET /occupations?q=desarroll` | 436 ocupaciones CIUO-08. Las 20 destacadas tienen `is_featured: true`. Las que no aplican a la región, `is_excluded` y `exclusion_reason` |
| Ranking del ISE (mejores y peores 20) | `GET /employability?view=top\|bottom&country=&sector=&featured=&year=` | Como mucho 2 ocupaciones por grupo CIUO. `group_hidden` dice cuántas del grupo quedaron afuera |
| Tabla completa ordenable | `GET /employability?view=all&sort_by=score\|net_demand\|salary_ppp\|insertion_rate\|automation_risk\|coverage\|occupation\|isco\|country&order=asc\|desc&limit=50&offset=0` | |
| Detalle del puntaje | El mismo, en `items[].components[]` | Por dimensión: `label`, `raw` (valor original), `normalized` (0-100), `weight`, `contribution` (los aportes suman el puntaje), `detail` (períodos y fuente) y `available` |
| Rangos y definiciones de cada dimensión | El mismo, en `dimension_ranges[]` | `definition`, `unit`, `possible_range`, `observed_min` y `observed_max` |
| Perfil de una ocupación | `GET /occupations/2512` | `hierarchy` (gran grupo › subgrupo › ocupación), `employability` (ISE por país), `latest` (empleo, salario y exposición por país), `groups` (de qué grupo CIUO sale cada dato) y `top_skills` |
| Evolución del ISE | `GET /employability/history?occupation=2512&country=ARG,URY` | |
| Habilidades de la ocupación | `GET /occupations/2512/skills?skill_type=knowledge\|skill&limit=` | `weight` de 0 a 1 y `skill_type_label` |

El ISE es relativo: 0 a 100 dentro del grupo comparado. `coverage_ratio` es la parte del peso con
datos; hoy el máximo es 0,75. `level` puede ser `insufficient_data` o `not_applicable`: en ese caso
`score` viene en `null`.

### Formación

Esta pantalla tampoco tiene diseño todavía.

| Elemento | Endpoint | Notas |
|---|---|---|
| Brechas de habilidades | `GET /skills/gaps?country=CHL&view=top\|bottom\|all&sort_by=gap\|demand_growth\|supply_growth\|occupations&min_occupations=&emerging=&q=` | `gap` en puntos porcentuales (fracción), `is_emerging` y `data_sufficiency_label`. Mientras `crosswalk_reviewed` sea `false`, mostrar el aviso "correspondencia carrera → ocupación en revisión". Hoy tienen brechas Chile y Argentina |
| Desajuste educación-ocupación (los 3 países) | Serie: `overeducation_rate` y `undereducation_rate` como cualquier indicador. Detalle: `GET /education-mismatch?country=ARG&year=` | El detalle trae los ocupados (miles) por gran grupo y nivel educativo, con `status` por celda (`matched`, `over`, `under`, `excluded`), los totales, las tasas (`over_rate`, `under_rate`, en fracción) y `explanation` (párrafos de "¿Cómo se calcula?"). Así se puede mostrar de dónde sale cada porcentaje. Sin `year`: el último año con datos; `years` lista los disponibles |
| Buscar habilidades | `GET /skills?q=datos` | Ordenadas por cuántas ocupaciones las usan |
| Detalle de una habilidad | `GET /skills/{código}` | `used_by`: ocupaciones que la usan |
| Carreras y ocupaciones para las que forman | `GET /graduates/crosswalk?country=CHL` (`&format=csv` para descargar) | |
| Egresados de las 19 carreras seleccionadas por Data Analytics | `GET /graduates/trends?country=CHL` y `/graduates/projections?country=CHL` | Los datos vienen con `pais` en minúsculas (`chile`), como los entrega Data Analytics |

### Alertas

| Elemento | Endpoint | Notas |
|---|---|---|
| Panel | `GET /alerts?country=&severity=high\|medium\|low&alert_type=&unread=` | `severity_label`, `alert_type_label`, `message`, `period`, `previous_value` → `current_value`, `detected_at`. `by_severity` da los totales por severidad |
| Explicación de cada tipo | `GET /alerts/rules` | Qué detecta cada tipo, umbrales en uso y qué significa cada severidad |
| Marcar como leída | `PATCH /alerts/{id}` con body `{"is_read": true}` · `POST /alerts/read-all` | Requiere `X-API-Key` |

### Administración

| Elemento | Endpoint | Notas |
|---|---|---|
| Estado de las fuentes | `GET /sources` | `status`: `ok`, `stale` (desactualizada), `unavailable` o `never_run`. También `last_success_at` y `last_run` |
| Historial de actualizaciones | `GET /sources/{código}/runs` | |
| Correcciones de la fuente | `GET /sources/{código}/revisions?dataset=&run_id=` | Cada valor que una carga posterior cambió (`revised`) o quitó (`removed`), con el valor anterior (`old_value`) y el nuevo. Útil para mostrar "la fuente corrigió este dato" |
| Actualizar ahora | `POST /sources/{código}/refresh` | Requiere `X-API-Key` |
| Qué archivos se pueden cargar | `GET /datasets/profiles` | Columnas obligatorias, hoja y origen oficial |
| Cargar un archivo | 1) `POST /datasets/upload` (multipart: `file`, `profile`, `declared_source_name`, `declared_source_url`, `reference_date`) → reporte y vista previa · 2) `POST /datasets/{id}/commit` | Requiere `X-API-Key`. Si el estado es `rejected`, mostrar `report.errors[]` (fila, columna y mensaje) |
| Historial de archivos | `GET /datasets?origin=download\|upload` | |

### Otros endpoints

- `GET /jobs?country=ARG&provincia=&sector=&q=&limit=&offset=` y `/jobs/summary?country=ARG`: ofertas de LinkedIn. **No son datos oficiales**; mostrar siempre el aviso. `/jobs/summary` trae también `view` (de `app.yaml → jobs_view`): el aviso completo, la nota al pie, el orden de los sectores (con "Otros" al final), el tamaño de página y las etiquetas de fuente y período. El Explorer (sección "Ofertas de empleo (LinkedIn)") reproduce la vista del primer prototipo en Next.js con esos datos: tarjetas, tabla sector × provincia que filtra al hacer clic, total por sector y listado paginado.
- `GET /coverage?country=ARG`: cobertura por país y sector del equipo de Data Analytics.

---

## 3. Pendientes conocidos

- **Login y roles:** el mockup tiene login y rol "Administración", pero la API todavía no tiene autenticación de usuarios.
- **URL de producción:** se define con el despliegue y la base en Supabase.
- **Dashboard actual (`backend/frontend`):** usa solo `/jobs`, `/coverage` y `/graduates/*`. Para las pantallas del mockup hay que sumar los endpoints de esta guía.
