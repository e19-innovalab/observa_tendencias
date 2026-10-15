# Backen App Test

Observatorio predictivo de tendencias laborales y educativas del Cono Sur (Argentina, Uruguay y Chile).

## Estructura

```
C:\rumbo_app
├── backend/   API en FastAPI + PostgreSQL (Supabase)
├── frontend/  Dashboard en Next.js (puerto 3010)
└── data/
    ├── raw/linkedin_jobs/   CSV de las búsquedas de Apify (no se sobrescriben)
    └── processed/           archivos limpios o derivados
```

El plan completo del backend está en `backend_plan_ES.md`.

## Requisitos

- Python 3.11 o superior
- Git
- Una base PostgreSQL (recomendado: un proyecto de [Supabase](https://supabase.com))

## Puesta en marcha del backend

Abrí PowerShell y ejecutá, paso a paso:

```powershell
cd C:\rumbo_app\backend

# 1. Crear y activar el entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -e ".[dev]"

# 3. Configurar variables de entorno
copy .env.example .env
```

Editá `backend\.env` y completá `DATABASE_URL` con la cadena de conexión de tu base
(en Supabase: Connect → Direct → método **Session pooler**; formato
`postgresql+psycopg://USUARIO:CLAVE@HOST:5432/postgres`). **No subas `.env` a git.**
Guía completa, con errores frecuentes: [`docs/conexion_supabase.md`](docs/conexion_supabase.md).

La base de Supabase **Rumbo** (región São Paulo) ya tiene las tablas y el catálogo cargados.
Solo hay que decirle a Alembic que la migración 0001 ya fue aplicada:

```powershell
# 4. Marcar la migración inicial como aplicada (NO uses "upgrade head" en esta base)
alembic stamp 0002

# Solo si usás una base nueva y vacía:
#   alembic upgrade head
#   python -m seeds.load

# 5. Cargar los CSV procesados (informe de cobertura y ofertas de LinkedIn) a la base
python -m app.ingestion.load_analytics

# 6. Levantar la API (usá otro puerto si el 8000 está ocupado)
uvicorn app.main:app --reload --port 8010
```

Comprobá que funciona:

- Estado del servicio: http://localhost:8010/health
- Documentación interactiva (OpenAPI): http://localhost:8010/docs
- Cobertura de datos: `GET /api/v1/coverage?pais=ARG`
- Ofertas de LinkedIn: `GET /api/v1/jobs?pais=ARG&provincia=Santa Fe&sector=Salud`
- Resumen provincia × sector: `GET /api/v1/jobs/summary?pais=ARG`

## Dashboard (frontend)

Con la API corriendo en el puerto 8010, en otra terminal:

```powershell
cd C:
umbo_approntend
npm install
copy .env.example .env.local     # NEXT_PUBLIC_API_URL=http://localhost:8010
npm run dev
```

Abrí http://localhost:3010. Muestra el resumen de ofertas, la tabla sector × provincia, el total por
sector, el listado con filtros y la cobertura de datos oficiales.

## Tests y calidad de código

```powershell
pytest
ruff check .
```

Los tests actuales no necesitan base de datos.

## Datos de Apify (ofertas de LinkedIn)

Guardá los CSV en `data\raw\linkedin_jobs\`, uno por búsqueda, con el nombre
`jobs_ar_AAAA-MM-DD.csv`. Cada archivo debe incluir la columna `scraped_at` (fecha de la corrida).
Nunca sobrescribas un archivo anterior: agregá uno nuevo.

Dos formas de obtenerlos:

1. **Desde la consola de Apify:** Storage → Datasets → elegí el dataset → Export → CSV.
2. **Con el script** `scripts\fetch_jobs.py` del proyecto del frontend. Requiere un token
   de https://console.apify.com/settings/integrations guardado como `APIFY_TOKEN` en un
   archivo local. Nunca pegues el token en el chat ni lo subas a git.

## Estado actual (Semana 0)

Hecho: esqueleto FastAPI, configuración, Alembic con la migración 0001, seeds del catálogo y
tests básicos.

Pendiente: Dockerfile y despliegue (Render o Railway), y definir el mapeo
ISIC de Tecnología vs. Economía del conocimiento (provisional en `backend\seeds\catalog.py`).

## Problemas frecuentes

- **No se puede ejecutar `Activate.ps1`:** ejecutá una vez
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **`alembic` falla al conectar:** revisá `DATABASE_URL` en `.env` y que la base acepte tu IP.
- **`pip install` dice "Multiple top-level packages":** actualizá `pyproject.toml` desde el repo;
  ya está corregido.
