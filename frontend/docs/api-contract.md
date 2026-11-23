# Contrato de API – Observa Tendencias (v0.1.0, desde openapi.json)

Base: `http://localhost:8010/api/v1` · Salud: `GET /health`.
Esquemas Zod del front: `frontend/src/lib/schemas/api.ts`.

## Convenciones reales de la API

- Países en ISO3: `ARG`, `URY`, `CHL`. Varios países se pasan separados por coma.
- Cada punto de dato trae `source`, `source_updated_at`, `fetched_at` y `data_type`
  (`observed` | `calculated` | `projected`). Las proyecciones traen `lower_bound` / `upper_bound`.
- La API manda las etiquetas ya traducidas (`*_label`): el front no traduce estados.
- Los textos de metodología llegan en markdown (`description_md`).
- Escritura (`PATCH /alerts/{id}`, `POST /alerts/read-all`, `POST /datasets/upload`,
  `/datasets/{id}/commit`, `/sources/{code}/refresh`) exige header `x-api-key`:
  solo desde el servidor de Next (Route Handlers), nunca desde el navegador.

## Mapa de pantallas a endpoints

| Pantalla / elemento | Endpoint |
|---|---|
| Filtro País | `GET /countries` |
| Filtro Sector | `GET /sectors` |
| Filtro Ocupación | `GET /occupations?featured=true&sector=` |
| Filtro Período | parámetros `from_year` / `to_year` (no hay endpoint, es un rango) |
| Sidebar de indicadores | `GET /indicators?domain=` (agrupar por `domain_label`) |
| KPI cards (Inicio y Panorama) | `GET /dashboard/summary?country=` (**country obligatorio**) |
| Gráfico año actual vs año pasado | `GET /compare?indicator=&countries=` (`current`, `previous`, `change`) |
| Serie histórica | `GET /observations?indicator=&country=&from_year=&to_year=` |
| Tendencias | `GET /trends?indicator=&country=&state=` |
| Proyecciones (con banda) | `GET /projections?indicator=&country=` |
| "Ver metodología" | `GET /methodologies/{type}` |
| Campana | `GET /alerts?unread=true` (`unread` = contador) |
| Ocupaciones | `GET /employability`, `GET /occupations/{code}`, `GET /jobs`, `GET /jobs/summary` |
| Formación | `GET /graduates/trends`, `/graduates/projections`, `/education-mismatch?country=` |
| Brechas de habilidades | `GET /skills/gaps`, `GET /skills/{code}` |
| Administración | `GET /datasets`, `/datasets/profiles`, `/sources`, `/sources/{code}/runs` |

## Cómo quedó conectada cada pantalla

- **`/inicio`**: promedio regional de los destacados de `GET /dashboard/summary` para ARG, CHL y
  URY + feed de `GET /alerts?limit=4`.
- **`/tendencias`**: catálogos reales, `GET /observations`, `GET /trends` y
  `GET /projections` según la pestaña. El filtro Frecuencia se aplica sobre los puntos ya
  devueltos (la API no acepta `frequency` como parámetro).
- **`/panorama-regional`**: `GET /dashboard/summary` + `GET /observations`; usa `io()` de
  `next/cache` para que los KPI se calculen por request.
- **`/sectores`**: `GET /employability?sector=&year=&country=&view=all` (hasta 500 filas).
  La API no expone un ISE sectorial: el promedio y los componentes se agregan en el front a
  partir de las ocupaciones del sector. La comparativa intersectorial hace una llamada por
  cada sector del catálogo.
- **`/ocupaciones`**: `GET /employability?view=all&sort_by=score&order=&year=&sector=&country=`
  con `limit=20` y `offset`. La paginación usa `scored_total` (excluye filas sin puntaje) y
  descarta las filas sin `score` que la API deja al final de `view=all`.
- **`/ocupaciones/[code]`**: `GET /occupations/{code}` (perfil, empleabilidad por país,
  habilidades ESCO y jerarquía CIUO), `GET /employability/history?occupation=&country=` y
  `GET /indicators` para traducir los códigos de `latest`.
- **`/habilidades`**:
  - Brechas: `GET /skills/gaps?view=all&sort_by=gap&order=&min_occupations=&emerging=` con
    paginación. La brecha se invierte en pantalla (`-gap × 100`) para que los déficits queden
    negativos, como en el diseño.
  - Proyecciones: `GET /graduates/projections` (solo Chile, 2026–2029). La API **no publica
    proyecciones de brechas de habilidades**; la pantalla lo aclara de forma explícita.


## Lo que el diseño pide y la API no tiene

1. **Login, registro y roles**: no existen endpoints de autenticación ni `/me`.
2. **Fecha de actualización en graduados**: los items de `/graduates/*` no traen
   `source_updated_at`.
3. **Campos en español** en `/graduates/*` y `/jobs` (`pais`, `nombre`, `provincia`),
   y parámetros duplicados `country` / `pais`.
4. **Alertas** tienen `is_read` global, no por usuario.
5. **No hay endpoint de filtros combinados**: cada filtro sale de un catálogo distinto.

## Pendientes ⚠️

- Confirmar `change_kind` (`absolute` | `relative`) y cómo mostrarlo en la pill del KPI.
- Definir qué `trend_state` / `assessment` se muestran y con qué color.
- Esquemas Zod faltantes: employability, jobs, skills, graduates, education-mismatch, sources, datasets.