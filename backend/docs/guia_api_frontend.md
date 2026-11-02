# Guía de la API para el frontend

Qué endpoint alimenta cada pantalla del mockup ("Wireframes Observatorio Innova Lab" en Figma),
qué devuelve y qué convenciones seguir. Estado al 18/10/2026.

- **Base URL (local):** `http://localhost:8010/api/v1`. La URL de despliegue se define más adelante, junto con Supabase.
- **Documentación interactiva** (todos los parámetros y esquemas): http://localhost:8010/docs. Se puede importar en Postman desde `http://localhost:8010/openapi.json`.
- **Implementación de referencia:** el Explorer (http://localhost:8010/explorer, código en `backend/backend/app/static/explorer.html`) usa todos estos endpoints. Si hay dudas de cómo llamar a uno, está ahí.
- **CORS:** los orígenes permitidos se configuran en `backend/.env` (`CORS_ORIGINS`). Por defecto, `http://localhost:3000` y `http://localhost:3010`.

---

## 1. Convenciones

### Textos: siempre desde la API

Etiquetas, nombres y mensajes llegan listos en español: `domain_label`, `data_type_label`,
`trend_state_label`, `level_label`, `severity_label`, `message`, entre otros. **No los escriban en
el frontend.** Si cambia un texto, se cambia en la configuración del backend y la interfaz lo toma
sola.

Las pantallas del ISE (ficha de ocupación y sectores) reciben además un bloque `texts`
(`app.yaml → employability`): `terms` (explicaciones de "Escalado" y "Aporte al ISE" para mostrar
al pasar el mouse), `unit_formats` (cómo se escribe un valor de cada unidad, por ejemplo
`"USD {value} / mes"`: reemplazar `{value}` por el número ya formateado) y `display` (etiqueta y
nota de los valores que se muestran primero, como el salario en USD).

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
| `usd_month` | USD por mes, al tipo de cambio de mercado |
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
| Sección "Brecha generacional" (debajo de la primera pantalla) | `GET /generational-gap?country=` | `title`, `description`, `source`; `youth` y `total` (los dos indicadores); `countries[]` con `headline` (frase lista para mostrar), `latest` y `points[]` por año (`year`, `youth`, `total`, `ratio`). La frase se edita en `app.yaml → generational_gap.headline` |

### Tendencias y proyecciones

| Elemento | Endpoint | Notas |
|---|---|---|
| Pestaña Tendencias | `GET /trends?indicator=...&country=...&from_year=&to_year=` | `trend_state_label` (Crecimiento, Estabilidad o Disminución) y `assessment_label` (Favorable, Desfavorable o Neutral, según si al indicador le conviene subir). Sin período: la última ventana guardada (`window_mode: "latest"`), con `previous_trend_state`. Con período: calculada para esos años (`window_mode: "range"`) |
| Lista de indicadores por grupo | `GET /trends?domain=labor&country=ARG` | Todas las tendencias de un dominio |
| Pestaña Proyecciones, gráfico "Tendencia actual / Proyección" | `GET /projections?indicator=...&country=...&from_year=` | `items[].observed` (línea continua) y `items[].projected` (línea punteada; `lower_bound` y `upper_bound` para la banda) |
| Recuadro "Fuente, Actualización, Ver metodología" | `GET /methodologies/trend` o `/methodologies/projection` | `description_md` y `params` |
| Burbujas "Las ocupaciones en movimiento" | `GET /occupation-groups/motion?y=growth\|ai_exposure\|employability&country=` | `points[]` por país, gran grupo y año: `x` (USD), `x_secondary` (USD PPA), `size` (ocupados), `y` y `carried` (valores repetidos del año anterior). `years`, `groups`, `y_options` para el selector, `x`, `y` y `size` con etiqueta, escala y dominio, y `notes` |

### Ocupaciones

Esta pantalla no tiene diseño en el mockup todavía. Esto es lo que ofrece la API:

| Elemento | Endpoint | Notas |
|---|---|---|
| Buscador y lista | `GET /occupations?featured=true` o `GET /occupations?q=enfermeria` | `q`: cada palabra tiene que coincidir con el comienzo de una palabra del nombre, en cualquier orden y sin importar tildes, plural ni género ("enfermera" encuentra "enfermería"); un número busca por código CIUO. También encuentra nombres locales ("remisero" → 8322, de `config/reference/ocupaciones_nombres_locales.yaml`). 436 ocupaciones CIUO-08. Las 20 destacadas tienen `is_featured: true`. Las que no aplican a la región, `is_excluded` y `exclusion_reason` |
| Ranking del ISE (mejores y peores 20) | `GET /employability?view=top\|bottom&country=&sector=&featured=&year=` | Como mucho 2 ocupaciones por grupo CIUO. `group_hidden` dice cuántas del grupo quedaron afuera |
| Tabla completa ordenable | `GET /employability?view=all&sort_by=score\|net_demand\|salary_ppp\|insertion_rate\|automation_risk\|coverage\|occupation\|isco\|country&order=asc\|desc&limit=50&offset=0` | |
| Detalle del puntaje | El mismo, en `items[].components[]` | Por dimensión: `label`, `raw` (valor original), `normalized` (0-100), `weight`, `contribution` (los aportes suman el puntaje), `detail` (períodos y fuente) y `available`. Salario: `display` trae el valor a mostrar primero (USD al tipo de cambio de mercado, mismo período que `raw`, con `label` y `note`); `raw` sigue en USD PPA, que es lo que usa el ISE. Se configura en `app.yaml → employability.display_values`. En `/employability/sectors`, `salary_usd_average` junto a `salary_ppp_average`. `/occupations/{código}` y `/employability/sectors` traen `texts` (ver "Textos: siempre desde la API") |
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
| Brechas de habilidades | `GET /skills/gaps?country=CHL&view=top\|bottom\|all&sort_by=gap\|demand_growth\|supply_growth\|occupations&min_occupations=&emerging=&q=&sector=&relation=essential\|any&occupation=` | `gap` en puntos porcentuales (fracción), `is_emerging` y `data_sufficiency_label`. Cada ítem trae `sectors` (sector, relación ESCO esencial/opcional y ocupaciones) e `is_cross_sector` (esencial en dos o más sectores: mostrar "Transversal"). `sector=` deja las habilidades esenciales del sector; `relation=any` suma las opcionales. Mientras `crosswalk_reviewed` sea `false`, mostrar el aviso "correspondencia carrera → ocupación en revisión". Hoy tienen brechas Chile y Argentina |
| Brechas por grupo de habilidades | `GET /skills/groups/gaps?country=&view=top\|bottom\|all&sector=&relation=&q=` | Igual que `/skills/gaps` pero por grupo de la jerarquía de ESCO: `group` (código, nombre, descripción, grupo superior), `skills` (cuántas habilidades de ESCO junta) y `top_skills` (con su `description`). Recomendado como vista principal |
| Desajuste educación-ocupación (los 3 países) | Serie: `overeducation_rate` y `undereducation_rate` como cualquier indicador. Detalle: `GET /education-mismatch?country=ARG&year=` | El detalle trae los ocupados (miles) por gran grupo y nivel educativo, con `status` por celda (`matched`, `over`, `under`, `excluded`), los totales, las tasas (`over_rate`, `under_rate`, en fracción) y `explanation` (párrafos de "¿Cómo se calcula?"). Así se puede mostrar de dónde sale cada porcentaje. Sin `year`: el último año con datos; `years` lista los disponibles |
| Buscar habilidades | `GET /skills?q=ganado asesorar` | Misma regla de `q` que `/occupations` (palabras en cualquier orden, sin tildes, plural ni género). Ordenadas por cuántas ocupaciones las usan |
| Detalle de una habilidad | `GET /skills/{código}` | `used_by`: ocupaciones que la usan |
| Carreras y ocupaciones para las que forman | `GET /graduates/crosswalk?country=CHL` (`&format=csv` para descargar) | Cada carrera trae su campo CINE-F 2013 (`cine_f`, `cine_f_name`), si es técnica (`technical`) y sus ocupaciones CIUO-08; `via` indica la tabla común campo → ocupación |
| Egresados de las 19 carreras seleccionadas por Data Analytics | `GET /graduates/trends?country=CHL` y `/graduates/projections?country=CHL` | Los datos vienen con `pais` en minúsculas (`chile`), como los entrega Data Analytics |

### Indicadores temáticos: Moctezuma, Ludita, Reina Roja y Sísifo

Cada uno tiene su pantalla. Comparten la forma de la respuesta: `items[]` (con `score`,
`level_label`, `components[]` por dimensión y la metodología en `methodology`), `available_years`
para el selector de año, `year` y `level_labels`; los rankings traen además `total`, `limit` y
`offset`. Texto y `params` de cada metodología en
`GET /methodologies/{moctezuma_index|ludita_index|red_queen_index|sisyphus_index}`). Los textos que
explican cada gráfico se arman con esos `params` y los datos: no hay que escribirlos a mano.
Criterios en `fuentes_y_criterios.md`, sección 7.

| Pantalla | Elemento | Endpoint | Notas |
|---|---|---|---|
| Moctezuma | Ranking y plano Ritmo × Capacidad | `GET /moctezuma?country=&sector=&featured=&year=&view=top\|bottom\|all` | `sides[]`, `side_labels` y `dimension_ranges` para los ejes y la guía de lectura; `pace` y `readiness` en cada ítem |
| Moctezuma | Evolución por país | `GET /moctezuma/countries?country=` | Promedio y niveles por año |
| Moctezuma | Evolución de una ocupación | `GET /moctezuma/history?occupation=2512&country=` | |
| Moctezuma | Gráfico histórico 1518–1568 | `GET /moctezuma/reference` | `points[]` (población y su puntaje), `events` (hitos), `point_labels`, `point_notes`, `alternative` (Rosenblat) y `sources` |
| Ludita | Ranking, cuadrante y filtro por camino | `GET /ludita?country=&path=weaver\|teller\|other_causes\|out_of_reach&year=&view=` | `path`, `path_label`, `exposure` y `vitality` en cada ítem; `paths[]` con las etiquetas y `path_rules` con los umbrales |
| Ludita | Evolución por país | `GET /ludita/countries?country=` | Cuántas ocupaciones hay en cada camino por año |
| Ludita | Casos históricos frente a hoy | `GET /ludita/history?country=` | `cases[]`: tejedores, operadoras telefónicas y cajeros (base 100 al llegar la tecnología); `today`: el gran grupo 4 desde 2022; `zoom_years` |
| Reina Roja | Ranking y detalle de una ocupación | `GET /red-queen?year=&country=&career=&view=&limit=&offset=` | `turnover`, `half_life` y, por fuente en `components[]`: `from_version`, `to_version`, `years`, `added_count`, `removed_count`, `renamed_count`, `new_per_year`, `added` y `removed` (listas completas; `examples_shown` dice cuántas mostrar antes de desplegar). `career` necesita `country` |
| Reina Roja | Medianas por año | `GET /red-queen/years` | |
| Reina Roja | Filtro por carrera | `GET /red-queen/careers?country=URY` | `career` y cuántas ocupaciones tiene |
| Sísifo | Grupos, cuadrante y selector de año | `GET /sisyphus?country=&year=` | `excluded_groups` (1 a 3), `quadrants` y `quadrant_rules`; `groups[]` con la definición y ocupaciones de ejemplo de cada gran grupo, y `groups_source` (enlace a la OIT). Cada ítem: `overeducation`, `earnings_ratio`, `earnings_usd`, `earnings_ppp`, `tertiary_ppp`, `quadrant_label` |
| Sísifo | Vista por país | `GET /sisyphus/countries?country=` | `graduates_below_share` y `premium` por año |

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
| Plantilla y ejemplos | `GET /datasets/profiles/{código}/template?format=xlsx\|csv` · `GET /datasets/profiles/{código}/examples/{nombre}` | Solo formatos con `has_template` (la plantilla genérica). El Excel tiene la hoja de datos solo con encabezados, instrucciones con filas de ejemplo y hojas con los códigos válidos (indicadores, países, sectores, ocupaciones). Los nombres de los ejemplos vienen en `example_files` del formato |
| Cargar un archivo | 1) `POST /datasets/upload` (multipart: `file`, `profile`, `declared_source_name`, `declared_source_url`, `reference_date`) → reporte y vista previa · 2) `POST /datasets/{id}/commit` con `{"confirm_overlap": true}` si hace falta | Requiere `manage_data`. Antes de leerlo se revisa que el archivo sea lo que dice: un `.xlsx` real sin macros, o un CSV de texto en UTF-8, con un máximo de filas y de tamaño. Si el estado es `rejected`, mostrar primero `report.groups[]`: cada problema una vez, con cuántas filas, cuáles, qué valores y `hint` (qué hacer). Después, `report.errors[]` fila por fila. Si `report.overlaps.count` > 0, el archivo repite valores que ya publicó una fuente oficial: mostrar `overlaps.message` y pedir confirmación. Sin `confirm_overlap` la carga responde `409`. Los valores se guardan como fuente aparte y no reemplazan el dato oficial |
| Historial de archivos | `GET /datasets?origin=download\|upload` | |

### Asistente ("Preguntale al Observatorio")

Responde preguntas con los datos del observatorio. Por dentro solo puede consultar endpoints de lectura de esta misma API (los de `app.yaml → assistant.tools`): no tiene acceso a la base, a internet ni a nada que modifique datos.

| Elemento | Endpoint | Notas |
|---|---|---|
| Estado y textos | `GET /assistant` | `enabled`; `texts` (título, ejemplo para el campo de texto, aviso); `max_question_chars`; `history_turns`; `remaining_today` (preguntas que le quedan hoy a quien inició sesión, `null` sin sesión) |
| Preguntar | `POST /assistant/ask` con body `{"question", "context"?, "history"?}` | Requiere sesión (permiso `view`). Ver abajo |

**Body.**
- `context`: lo que la persona está mirando, todo opcional: `{"page": "/ocupaciones/2221", "country": "CHL", "occupation": "2221", "sector": "health"}`. Permite preguntas como "¿y en Uruguay?" desde una ficha.
- `history`: los turnos anteriores `[{"role": "user"|"assistant", "content"}]`. El servidor no guarda la conversación; mandar como mucho `history_turns` pares.
- `choice`: lo que la persona eligió de las opciones de la respuesta anterior, `{"occupation": "2221"}` o `{"country": "URY"}`. Se manda junto con la misma pregunta.

**Respuesta.**
- `answer`: el texto para mostrar.
- `links[]` (`label`, `href`): las páginas del frontend con los mismos datos que usó. Mostrarlas debajo de la respuesta.
- `status`:
  - `ok`;
  - `unverified`: algún número de la respuesta no aparece en los datos consultados. Mostrar `warning` destacado; los números van en `unverified_numbers`;
  - `blocked`: la respuesta se reemplazó por un aviso, si `numbers_check.on_unverified` es `block`;
  - `refused`: el modelo no quiso responder.
- `verified`: `true` solo con `status: ok`.
- `tool_calls[]`: qué consultó (`tool`, `args`, `ok`), por si se quiere mostrar "Consultó: ficha de 2221".
- `options[]` (`label`, `occupation` o `country`): cuando la pregunta es ambigua (varias ocupaciones, falta el país), botones para elegir. Al tocar uno, repetir la pregunta con `choice`.
- `source`: `script` (respondida con una plantilla y los datos, sin modelo: instantánea y sin costo) o `model`.
- `remaining_today`, `provider`, `model`, `log_id`.

**Errores.**
- `401`: sin sesión.
- `422`: pregunta vacía o demasiado larga.
- `429`: límite diario de la persona o del sistema.
- `503`: asistente apagado o el modelo no responde.

El texto de cada error viene en `detail` (de `assistant.messages`). Con un modelo local en CPU una respuesta puede tardar más de un minuto: mostrar un estado de espera y un botón para detener.

**Respuestas por plantilla.** Las preguntas frecuentes (salario, empleabilidad, habilidades de una ocupación; ranking y sectores de un país; cómo se calcula el ISE) se responden con plantillas de `app.yaml → assistant.scripted` y los datos de la API, sin modelo. Reconocen la ocupación por código, por nombre o por nombre local ("remisero", de `config/reference/ocupaciones_nombres_locales.yaml`). No cuentan para el límite diario. Lo que no encaja en una plantilla lo responde el modelo.

**Detener.** Si el cliente cierra el pedido (la persona tocó "Detener"), el backend detiene el modelo. La pregunta queda en el registro como `cancelled` y no cuenta para el límite del día.

### Otros endpoints

- `GET /jobs?country=ARG&provincia=&sector=&q=&limit=&offset=` y `/jobs/summary?country=ARG`: ofertas de LinkedIn. **No son datos oficiales**; mostrar siempre el aviso. `/jobs/summary` trae también `view` (de `app.yaml → jobs_view`): el aviso completo, la nota al pie, el orden de los sectores (con "Otros" al final), el tamaño de página y las etiquetas de fuente y período. El Explorer (sección "Ofertas de empleo (LinkedIn)") reproduce la vista del primer prototipo en Next.js con esos datos: tarjetas, tabla sector × provincia que filtra al hacer clic, total por sector y listado paginado.
- `GET /coverage?country=ARG`: cobertura por país y sector del equipo de Data Analytics.

---

## 3. Pendientes conocidos

- **URL de producción:** se define con el despliegue y la base en Supabase.
- **Dashboard viejo (`backend/frontend`):** usa solo `/jobs`, `/coverage` y `/graduates/*`. Los frontends nuevos (`frontend/frontend` y `frontend/frontend_minimal`) ya usan los endpoints de esta guía, con inicio de sesión y roles (`/auth/login`, `/auth/me`).
- **Carga manual, segunda etapa:** retirar una carga y marcar en las pantallas los datos de carga manual. La API todavía no los distingue en las series: hay que agregar ese dato a la respuesta antes de mostrarlo.
- **Asistente:** el modelo que responde lo que no cubren las plantillas está en evaluación. Los textos y el comportamiento de la pantalla no cambian, porque vienen de `GET /assistant`.
