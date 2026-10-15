# Conexión del backend a Supabase

Cómo conectar la API de Rumbo (`backend/`) a la base de datos en Supabase, y cómo resolver los problemas
más comunes.

## Datos del proyecto

| Dato | Valor |
|---|---|
| Proyecto | **Rumbo** |
| ID del proyecto (`ref`) | `mfoiqrnmzbipjfsitnbi` |
| Región | São Paulo (`sa-east-1`) |
| Base de datos | `postgres` |
| Plan | Free |

La contraseña de la base **no está en ningún archivo del repositorio ni en este documento**. Se definió al crear
el proyecto y se puede restablecer en Supabase: Project Settings → Database.

## Cómo funciona la conexión

El backend (Python) se conecta **directo a PostgreSQL** con SQLAlchemy y el driver `psycopg`. No usa la API
pública de Supabase, y por eso las tablas tienen RLS (row level security) activado y sin políticas: la API pública
no puede leerlas. Solo se accede con la cadena de conexión del backend.

El dashboard (`frontend/`) nunca habla con la base: llama a la API de FastAPI en el puerto 8010.

## Paso a paso

### 1. Crear el archivo `.env`

```powershell
cd C:\rumbo_app\backend
copy .env.example .env
```

`.env.example` está en `backend\.env.example`. El nombre empieza con punto, así que el Explorador de Windows puede
ocultarlo; en VS Code se ve dentro de `backend`.

### 2. Obtener la cadena de conexión: usá el Session pooler

En Supabase: botón **Connect** → pestaña **Direct** (Connection string) → en el método de conexión elegí
**Session pooler**.

> **No uses la conexión directa** (`db.mfoiqrnmzbipjfsitnbi.supabase.co`). Ese host solo tiene dirección IPv6, y si
> tu red no tiene IPv6 falla con `failed to resolve host` o `unreachable network`. El Session pooler funciona por
> IPv4.

La cadena del pooler tiene esta forma:

```
postgresql://postgres.mfoiqrnmzbipjfsitnbi:[TU-CLAVE]@aws-1-sa-east-1.pooler.supabase.com:5432/postgres
```

Diferencias con la conexión directa:

| | Directa (no usar) | Session pooler (usar) |
|---|---|---|
| Usuario | `postgres` | `postgres.mfoiqrnmzbipjfsitnbi` |
| Host | `db.mfoiqrnmzbipjfsitnbi.supabase.co` | `aws-1-sa-east-1.pooler.supabase.com` |
| Puerto | 5432 | 5432 |

### 3. Completar `DATABASE_URL` en `.env`

Copiá la cadena y cambiá **solo el comienzo**, de `postgresql://` a `postgresql+psycopg://`:

```
DATABASE_URL=postgresql+psycopg://postgres.mfoiqrnmzbipjfsitnbi:TU_CLAVE@aws-1-sa-east-1.pooler.supabase.com:5432/postgres
```

Puntos importantes:

- Reemplazá `TU_CLAVE` por la contraseña real, **sin corchetes**.
- Si la contraseña tiene caracteres especiales, codificalos: `@` → `%40`, `#` → `%23`, `/` → `%2F`,
  `:` → `%3A`, `%` → `%25`.
- El host del pooler es `aws-1-…`. Hay un `aws-0-…` que también existe, pero **no sirve para este proyecto**
  (da error `ENOTFOUND`). Copiá siempre el host exacto que muestra Supabase; no escribas una `X` ni adivines.
- Después de editar `.env`, **reiniciá la API**: el modo `--reload` no detecta cambios en `.env`.

### 4. Probar la conexión

Con el entorno virtual activo, en `backend`:

```powershell
python -c "from sqlalchemy import create_engine, text; from app.core.config import settings; print(create_engine(settings.database_url).connect().execute(text('select current_database()')).scalar())"
```

Si imprime `postgres`, la conexión funciona.

### 5. Preparar las tablas y cargar los datos

Las tablas ya existen en Supabase (se crearon con las migraciones de Alembic aplicadas desde MCP). Solo hay que
decirle a Alembic que están al día y cargar los CSV:

```powershell
alembic stamp 0002
python -m app.ingestion.load_analytics
```

- `alembic stamp 0002` marca la migración 0002 como aplicada. **No uses `alembic upgrade head`** en esta base: las
  tablas ya existen y daría error.
- `load_analytics` lee `data/processed/data_analytics/informe_cobertura.csv` y `ofertas_linkedin.csv` y los
  carga con upsert, así que se puede repetir sin duplicar filas.
- En una base nueva y vacía el orden sería `alembic upgrade head`, `python -m seeds.load` y luego
  `load_analytics`.

### 6. Levantar la API y verificar

```powershell
uvicorn app.main:app --port 8010
```

- http://localhost:8010/api/v1/jobs/summary?pais=ARG debe devolver `"total": 640`.
- http://localhost:8010/docs es la documentación interactiva.

## Tablas en Supabase

`countries`, `sectors`, `occupations`, `occupation_crosswalks`, `skills`, `occupation_skills`, `sources`,
`ingestion_runs`, `indicators`, `coverage_report` y `job_postings`. Las dos últimas alimentan el dashboard.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| Swagger queda en "LOADING" o la API responde 503 *«No se pudo conectar a la base de datos»* | Falta `backend\.env`, o `DATABASE_URL` es incorrecta. Revisá el host, el usuario y que hayas reiniciado la API. |
| `failed to resolve host 'db.…supabase.co'` / `unreachable network` | Estás usando la conexión directa (solo IPv6). Cambiá al Session pooler. |
| `failed to resolve host 'aws-X-…'` | Quedó un marcador de posición. El host real es `aws-1-sa-east-1.pooler.supabase.com`. |
| `FATAL: (ENOTFOUND)` o `Tenant or user not found` | Host del pooler equivocado (`aws-0-` en vez de `aws-1-`) o falta el sufijo del proyecto en el usuario (`postgres.mfoiqrnmzbipjfsitnbi`). |
| `password authentication failed` | Contraseña incorrecta o sin codificar. Restablecela en Project Settings → Database. |
| Cambié `.env` y no pasa nada | Reiniciá la API (`Ctrl+C` y volver a ejecutar `uvicorn`). |
| `relation … already exists` al correr Alembic | Usaste `upgrade head` en esta base. Usá `alembic stamp 0002`. |

## Seguridad

- `backend\.env` contiene la contraseña de la base. Está en `.gitignore`; **no lo subas a git ni lo compartas**.
- Nunca pegues la contraseña en un chat ni en un mensaje de commit.
- La clave «publishable» (`sb_publishable_…`) de Supabase es pública por diseño, pero este backend no la usa. No
  uses nunca una clave `service_role` en el frontend.
- Si la contraseña se expone, restablecela de inmediato en Supabase.
