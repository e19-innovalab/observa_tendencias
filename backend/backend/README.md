# Backend de Observa Tendencias

API FastAPI del observatorio, con PostgreSQL y autenticación Supabase.

## Requisitos

- Python 3.11 o superior.
- Docker Desktop para PostgreSQL local.

## Puesta en marcha en Windows (PowerShell)

Desde esta carpeta (`backend/backend`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Completa en `.env` los valores locales de PostgreSQL y las credenciales del proyecto Supabase.
Para auth se requieren `SUPABASE_URL`, `SUPABASE_ANON_KEY` y
`SUPABASE_REDIRECT_URL=http://localhost:3010/auth/callback`. Configura también
`CORS_ORIGINS=["http://localhost:3010"]`; deja `AUTH_COOKIE_SECURE=false` en desarrollo local.
El archivo `.env` contiene datos privados y no debe subirse al repositorio.

Luego, levanta la base de datos y la API:

```powershell
docker compose up -d
alembic upgrade head
python -m seeds.load
uvicorn app.main:app --reload --port 8010
```

La documentación interactiva de la API está en http://localhost:8010/docs.
Ejecuta las pruebas desde esta carpeta con `pytest`.
El Explorer del backend, con el estado de sesión, está disponible en http://localhost:8010/explorer.

## Proveedor Google

En Supabase, habilita Google en **Authentication → Sign In / Providers** y configura las
credenciales OAuth de Google. En **Authentication → URL Configuration**, permite
`http://localhost:3010/auth/callback` como URL de redirección.
