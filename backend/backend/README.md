# Observa Tendencias: backend

FastAPI + PostgreSQL (Supabase). La estructura sigue `backend_plan_ES.md`.

Las instrucciones completas están en [`../README.md`](../README.md). La aplicación necesita dos
procesos simultáneos: la API FastAPI (puerto `8010`) y el frontend Next.js (puerto `3010`).

### Preparación inicial (una sola vez)

**Windows (PowerShell, desde esta carpeta):**

```powershell
python -m venv .venv              # omitir si ya existe el entorno
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.example .env           # completar DATABASE_URL y credenciales Supabase
docker compose up -d
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m seeds.load
```

**macOS / Linux (bash, desde esta carpeta):**

```bash
python3 -m venv .venv            # omitir si ya existe el entorno
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env             # completar DATABASE_URL y credenciales Supabase
docker compose up -d
python -m alembic upgrade head
python -m seeds.load
```

Instala también las dependencias del frontend y prepara sus variables (desde esta carpeta):

Windows (PowerShell):

```powershell
cd ..\frontend
npm.cmd install
copy .env.example .env.local     # solo la primera vez; completar las variables NEXT_PUBLIC_SUPABASE_*
```

macOS / Linux (bash):

```bash
cd ../frontend
npm install
cp .env.example .env.local       # solo la primera vez; completar NEXT_PUBLIC_SUPABASE_*
```

### Iniciar la aplicación

Abre dos terminales y deja ambos procesos ejecutándose. Inicia primero el backend.

**Terminal 1 — Backend Python / FastAPI (Windows, PowerShell):**

```powershell
docker compose up -d
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8010
```

Deja el proceso de Uvicorn ejecutándose en esta terminal. La API queda en
`http://localhost:8010` (documentación: `/docs`; Explorer: `/explorer`).

**Terminal 1 — Backend Python / FastAPI (macOS / Linux, bash):**

```bash
docker compose up -d
source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8010
```

**Terminal 2 — Frontend Next.js (Windows, PowerShell):**

```powershell
cd ..\frontend
npm.cmd run dev
```

**Terminal 2 — Frontend Next.js (macOS / Linux, bash):**

```bash
cd ../frontend
npm run dev
```

Deja también abierto el proceso de Next.js y abre `http://localhost:3010`. El acceso está en
`http://localhost:3010/auth`. El frontend necesita que el backend siga ejecutándose. No es
necesario iniciar sesión para consultar el dashboard.

En PowerShell, ejecuta Uvicorn con el Python de `.venv` como en el comando anterior; el
`uvicorn.exe` global puede pertenecer a otro Python y no encontrar dependencias del proyecto.

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
`POST /api/v1/auth/session`, `GET /api/v1/auth/me` y `POST /api/v1/auth/logout` para establecer,
consultar y cerrar la sesión. En el alta, el nombre de usuario se guarda en los metadatos del
usuario de Supabase. La autenticación con contraseña se realiza con email, como requiere Supabase
Auth.

Completá `SUPABASE_URL` y `SUPABASE_ANON_KEY` en `.env` con la URL del proyecto y su clave pública
(publishable/anon). `SUPABASE_REDIRECT_URL` se usa para devolver al frontend los enlaces de
confirmación por email y debe estar permitida en Supabase, en **Authentication → URL Configuration
→ Redirect URLs**. Para Google, habilitá el proveedor en **Authentication → Providers → Google** y
configurá allí las credenciales OAuth de Google y la URL de callback de Supabase.

El frontend local escucha en el puerto `3010`. En Supabase, configurá **Site URL** y agregá
`http://localhost:3010/auth/callback` a **Redirect URLs**. Configurá también
`NEXT_PUBLIC_SUPABASE_URL` y `NEXT_PUBLIC_SUPABASE_ANON_KEY` en `frontend/.env.local`. El callback
PKCE intercambia el código con Supabase y entrega la sesión a la API; la API valida y conserva los
tokens en cookies `HttpOnly` para que el Explorer en `http://localhost:8010` pueda identificar al
usuario y renovar la sesión. `AUTH_COOKIE_SECURE=false` es solo para desarrollo local por HTTP;
en producción HTTPS debe configurarse como `true`. Los enlaces de confirmación son de un solo uso
y caducan; si un enlace devuelve `otp_expired`, solicitá uno nuevo y abrí el email más reciente.

Las variables de autenticación son opcionales para iniciar la API. Si no se configuraron, los
endpoints de autenticación responden `503` con un mensaje claro. Los tokens nunca se devuelven en
el cuerpo JSON ni se registran en logs; se conservan en cookies `HttpOnly`.
