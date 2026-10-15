# Scripts de datos

Scripts que transforman los datos de `data/raw` en archivos de `data/processed`.
Requieren el entorno del backend (`backend\.venv`), porque usan pandas.

| Script | Entrada | Salida |
|---|---|---|
| `build_ofertas_linkedin.py` | `raw/linkedin_jobs/*.csv` (exports de Apify) | `processed/data_analytics/ofertas_linkedin.csv` |
| `build_egresados_series.py` | `raw/egresados/indicadores_carrera_anio.csv` | `processed/data_analytics/egresados_series.csv` |
| `build_egresados_trends.py` | `processed/data_analytics/egresados_series.csv` | `egresados_tendencias.csv`, `egresados_proyecciones.csv` |

## Cómo ejecutarlos

Desde `C:\rumbo_app`:

```powershell
backend\.venv\Scripts\python data\scripts\build_ofertas_linkedin.py
backend\.venv\Scripts\python -m pytest data\scripts
```

El script imprime la cantidad de ofertas, una tabla de provincia por sector y cuántas ofertas
se clasificaron por industria, por título o quedaron sin regla.

## `build_ofertas_linkedin.py`

Alinea las ofertas de LinkedIn con las etiquetas de `processed/data_analytics/informe_cobertura.csv`.

**Columnas de salida:** `pais`, `provincia`, `sector`, `regla_clasificacion`, `id`, `titulo`,
`empresa`, `ubicacion`, `fecha_publicacion`, `nivel_experiencia`, `tipo_empleo`, `industria`,
`postulantes`, `url`, `scraped_at`.

- **`pais`:** siempre `ARG`.
- **`provincia`:** Buenos Aires, Córdoba o Santa Fe. Se toma del archivo de la búsqueda
  (`FILE_PROVINCE`), no del texto de ubicación de LinkedIn, que es inconsistente
  (por ejemplo "Greater Rosario").
- **`sector`:** Tecnología, Economía del conocimiento, Salud, Energía, Turismo u `Otros`
  (fuera de los cinco sectores).
- **`regla_clasificacion`:** `industria`, `titulo` o `ninguna`, para auditar cada asignación.
- **`scraped_at`:** fecha y hora (UTC) tomadas del nombre del archivo exportado.

**Cómo se asigna el sector:**

1. Primero por la industria de LinkedIn de la empresa (como hace CIIU/ISIC). Gana la primera
   regla que coincide, en este orden: Salud, Energía, Turismo, Tecnología, Economía del conocimiento.
2. Si no coincide, por palabras clave del título.
3. Si tampoco, queda como `Otros`.

Cada oferta recibe **una sola** etiqueta. Tecnología y Economía del conocimiento se superponen en
CIIU/ISIC (J62-63); acá las industrias de TI van a Tecnología y los servicios profesionales que no
son de TI (jurídicos, contables, consultoría, publicidad, diseño) van a Economía del conocimiento.
Esta decisión es provisional y debe confirmarse con el equipo.

**Limitaciones:**

- Es una clasificación por reglas, no un dato oficial. El sector es el de la **empresa**: un
  desarrollador en una petrolera cuenta como Energía.
- Es una instantánea de una semana de ofertas, no una serie de tiempo.
- LinkedIn no es una fuente oficial; mostrarla separada de los datos oficiales del informe de cobertura.

## Agregar una búsqueda nueva

1. Exportá el dataset de Apify como CSV y guardalo en `data/raw/linkedin_jobs/` (no sobrescribas
   archivos anteriores).
2. Sumá la marca de hora del nombre del archivo (por ejemplo `17-54-27`) y su provincia a
   `FILE_PROVINCE` en el script. Si falta, el script se detiene con un error que nombra el archivo.
3. Volvé a ejecutar el script.

## Tests

`test_build_ofertas_linkedin.py` verifica la clasificación de sectores (incluido que "Hospitality"
no se confunda con salud) y la detección de la provincia por archivo.

## `build_egresados_series.py`

Prepara la serie anual de graduados por carrera (Argentina y Chile) para tendencias y proyecciones.
Descarga `indicadores_carrera_anio.csv` de Drive (`data/processed`) y guardalo en
`data/raw/egresados/`; el script acepta también otra ruta como argumento.

- **Ceros de relleno:** antes de que exista un programa la fuente trae filas con `graduados = 0` y
  `carrera_objetivo = 0`. Se descartan los años anteriores al primer año con graduados.
- **Ceros intermedios:** se conservan y se marcan con `hueco = True`.
- **Género no informado:** en Argentina `mujeres` y `hombre` valen 0 aunque haya graduados; se
  reemplazan por vacío.
- **Columnas nuevas:** `n_anios_serie` y `elegible_tendencia` (al menos 4 años, igual que
  `app.analytics.trends`).

## `build_egresados_trends.py`

Aplica `app.analytics` a la salida de `build_egresados_series.py` (ejecutalo después de ese).

- **Tendencia:** `classify_trend` sobre los últimos 5 años de cada carrera. Si la ventana incluye
  un año con 0 graduados, queda `insufficient_data`.
- **Proyección:** `project_series` (Holt, 4 años) sobre la serie completa, solo con 12 o más años y
  sin huecos. El límite inferior se fija en 0. Son valores orientativos.
- **Columna `proyeccion`:** `generada`, `historia_insuficiente(<12)` o `con_huecos`.
- **Atención:** las variaciones porcentuales sobre bases chicas son enormes (por ejemplo, inteligencia
  artificial pasa de 46 a 1564 graduados). La tendencia es válida, pero el porcentaje no se debe mostrar
  sin la cantidad absoluta.
