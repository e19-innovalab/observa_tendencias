# Observa Tendencias: backend

API de Observa Tendencias construida con FastAPI y PostgreSQL. Se ejecuta desde esta
carpeta y escucha en el puerto `8010`.

## Requisitos

- Python, según `requires-python` en `pyproject.toml`.
- Docker Desktop para ejecutar PostgreSQL localmente.

## Preparación inicial

Ejecuta estos pasos desde `backend/backend/`.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.example .env
```

Edita `.env` y completa al menos `DATABASE_URL` y las credenciales de PostgreSQL
definidas allí. Para habilitar autenticación, configura también `SUPABASE_URL` y
`SUPABASE_ANON_KEY`. Luego inicia la base de datos y prepara el esquema:

```powershell
docker compose up -d
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m seeds.load
```

### macOS / Linux (bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

Completa en `.env` `DATABASE_URL` y las credenciales de PostgreSQL. Para habilitar
autenticación, configura también `SUPABASE_URL` y `SUPABASE_ANON_KEY`. Después:

```bash
docker compose up -d
python -m alembic upgrade head
python -m seeds.load
```

## Iniciar la API

Comprueba que Docker esté activo y que PostgreSQL esté levantado:

```bash
docker compose up -d
```

En Windows (PowerShell), ejecuta Uvicorn con el Python del entorno virtual:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8010
```

En macOS / Linux:

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8010
```

La documentación interactiva de la API queda disponible en
<http://localhost:8010/docs>; el endpoint de salud es
<http://localhost:8010/health>.

## Carga de datos

La migración y las semillas preparan el esquema y los catálogos. Para descargar datos
de las fuentes configuradas y cargarlos en analítica, ejecuta desde esta carpeta:

```bash
python -m app.jobs.run --all
python -m app.ingestion.load_analytics
```

En Windows, antepón `.\.venv\Scripts\python.exe` a cada comando de Python.

## Configuración opcional

- **Autenticación:** configura `SUPABASE_URL` y `SUPABASE_ANON_KEY`. Sin ellas, la API
  sigue funcionando y los endpoints de autenticación indican que el servicio no está
  configurado. `SUPABASE_REDIRECT_URL` define la URL de retorno permitida para enlaces
  de confirmación y autenticación; regístrala también en la configuración de Supabase
  Auth. Para Google, habilita el proveedor y sus credenciales en Supabase.
- **Seguridad de cookies:** `AUTH_COOKIE_SECURE=false` sirve para desarrollo local por
  HTTP; en producción con HTTPS debe establecerse en `true`.
- **Acceso de administración:** configura `ADMIN_API_KEY` para los endpoints
  administrativos.

No compartas ni subas el archivo `.env`; contiene credenciales del entorno.
