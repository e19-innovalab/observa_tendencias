# Observa Tendencias: backend

FastAPI + PostgreSQL (Supabase). La estructura sigue `backend_plan_ES.md`.

Las instrucciones completas de instalación y puesta en marcha están en
[`../README.md`](../README.md).

Resumen (desde esta carpeta, con el entorno virtual activo):

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.example .env           # completar DATABASE_URL
alembic upgrade head
.\.venv\Scripts\python.exe -m seeds.load
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8010
.\.venv\Scripts\python.exe -m pytest
```

La API queda en `http://localhost:8010` (documentación: `/docs`; Explorer: `/explorer`).
Para iniciar el frontend, en otra terminal:

```powershell
cd ..\frontend
npm.cmd install
npm.cmd run dev
```

El dashboard está en `http://localhost:3010` y el acceso opcional de autenticación en
`http://localhost:3010/auth`. No es necesario iniciar sesión para usar el dashboard.
En PowerShell, ejecutá Uvicorn con el Python de `.venv` como en el comando anterior; el
`uvicorn.exe` global puede pertenecer a otro Python y no encontrar dependencias como Supabase.

## Estructura del proyecto

```
backend/
├── app/
│   ├── main.py              # punto de entrada FastAPI
│   ├── api/v1/              # routers: alerts, catalog, coverage, datasets,
│   │                        #   employability, indicators, jobs, skills,
│   │                        #   sources, trends
│   ├── core/                # config.py, database.py
│   ├── models/              # modelos SQLAlchemy: analytics, base, catalog, sources
│   ├── schemas/             # esquemas de respuesta (analytics.py)
│   ├── connectors/          # conectores a fuentes externas (base, registry)
│   ├── ingestion/           # pipeline, uploads, load_analytics
│   ├── normalization/       # crosswalks, normalizer, periods, units
│   ├── analytics/           # alerts, employability, projections, skill_gaps, trends
│   ├── jobs/                # scheduler.py
│   └── services/
├── migrations/              # Alembic
├── seeds/                   # catalog.py, load.py
├── tests/                   # test_api, test_analytics_api, test_catalog_seed
├── alembic.ini
├── pyproject.toml
├── .env.example
└── backend_plan_ES.md       # plan de arquitectura
```

## Autenticación con Supabase

La API expone `POST /api/v1/auth/signup` para crear usuarios con nombre de usuario, email y
contraseña; `POST /api/v1/auth/login` para iniciar sesión con email y contraseña;
`POST /api/v1/auth/resend-confirmation` para solicitar otro correo de confirmación; y
`GET /api/v1/auth/google` para obtener la URL de inicio de sesión OAuth con Google. En el alta, el
nombre de usuario se guarda en los metadatos del usuario de Supabase. La autenticación con
contraseña se realiza con email, como requiere Supabase Auth.

Completá `SUPABASE_URL` y `SUPABASE_ANON_KEY` en `.env` con la URL del proyecto y su clave pública
(publishable/anon). `SUPABASE_REDIRECT_URL` debe ser la URL del frontend que procesará la respuesta
OAuth y también debe estar permitida en Supabase, en **Authentication → URL Configuration →
Redirect URLs**. Para Google, habilitá el proveedor en **Authentication → Providers → Google** y
configurá allí las credenciales OAuth de Google y la URL de callback de Supabase. El endpoint
`/auth/google` devuelve la URL a la que debe redirigir el navegador. El alta por email también usa
esa URL para devolver al usuario al frontend después de confirmar el correo.

El frontend local escucha en el puerto `3010`. En Supabase, configurá **Site URL** y agregá
`http://localhost:3010/auth/callback` a **Redirect URLs**. La aplicación muestra allí el resultado
de la confirmación. Los enlaces de confirmación son de un solo uso y caducan; si un enlace devuelve
`otp_expired`, solicitá uno nuevo y abrí el email más reciente.

Las variables de autenticación son opcionales para iniciar la API. Si no se configuraron, los
endpoints de autenticación responden `503` con un mensaje claro.

Después de un login exitoso, la API no devuelve ni almacena los tokens de Supabase. Solo registra
metadatos básicos de la sesión en el log del backend.
