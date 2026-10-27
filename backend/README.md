# Observa Tendencias · Observatorio de tendencias laborales y educativas

Observatorio predictivo de tendencias laborales y educativas del Cono Sur (Argentina, Uruguay y
Chile), del programa InnovaLab. Junta datos oficiales de empleo, salarios, educación y formación,
calcula tendencias, proyecciones, un Índice Sintético de Empleabilidad (ISE) por ocupación,
brechas de habilidades y alertas, y los expone en una API.

## Estructura

```
backend/                   (esta carpeta)
├── backend/               API en FastAPI + PostgreSQL
│   ├── app/               código: conectores, lectura de archivos oficiales, cálculos, API
│   ├── config/            toda la configuración (YAML): fuentes, indicadores, metodología, textos
│   ├── migrations/        migraciones de la base (Alembic)
│   ├── seeds/             carga del catálogo, fuentes e indicadores desde config/
│   ├── tests/             tests (no necesitan base de datos)
│   └── docker-compose.yml Postgres local
├── frontend/              dashboard y autenticación opcional en Next.js (puerto 3010)
├── data/
│   ├── raw/               archivos originales: ofertas de LinkedIn, egresados y archivos oficiales descargados
│   ├── processed/         archivos limpios o derivados (CSV del equipo de datos)
│   ├── uploads/           archivos cargados a mano desde la API
│   └── scripts/           scripts de preparación y de tablas de referencia
└── docs/                  documentación (ver abajo)
```

## Documentación

| Documento | Para qué |
|---|---|
| [`docs/fuentes_y_criterios.md`](docs/fuentes_y_criterios.md) | Fuentes, URLs, indicadores y criterios de cálculo: tendencias, proyecciones, ISE, brechas de habilidades, desajuste educación-ocupación, alertas e historial de datos |
| [`docs/guia_api_frontend.md`](docs/guia_api_frontend.md) | Qué endpoint alimenta cada pantalla del mockup |
| [`docs/pendientes_analytics.md`](docs/pendientes_analytics.md) | Revisiones y decisiones pendientes del equipo de Data Analytics |
| [`data/scripts/referencias/README.md`](data/scripts/referencias/README.md) | Ocupaciones CIUO-08, correspondencias carrera → ocupación de los tres países y los scripts que las generan |
| [`docs/solicitud_sies_empleabilidad.md`](docs/solicitud_sies_empleabilidad.md) | Pedido al SIES (Chile) de la base de empleabilidad por carrera, para la tasa de inserción del ISE |
| [`docs/conexion_supabase.md`](docs/conexion_supabase.md) | Cómo conectar a Supabase (para cuando se migre) |
| [`backend/backend_plan_ES.md`](backend/backend_plan_ES.md) | Plan completo del backend |

## Requisitos

- Python 3.11 o superior
- Docker Desktop (para la base PostgreSQL local)
- Git
- Node.js 18.18 o superior, solo para el prototipo en Next.js

## Puesta en marcha

Hoy se trabaja con una base **PostgreSQL local** en Docker (versión 17, la misma que Supabase).
Pasar a Supabase más adelante solo requiere cambiar `DATABASE_URL` en `.env`.

**macOS / Linux (Bash):**

```bash
# Ejecuta desde la raíz del repositorio:
cd backend/backend

# 1. Entorno virtual y dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Variables de entorno: crea .env solo si todavía no existe.
if [ ! -f .env ]; then cp .env.example .env; else echo ".env ya existe; se conserva."; fi
# Edita .env antes de continuar. Cambia, como mínimo, la contraseña de Postgres
# y ADMIN_API_KEY; DATABASE_URL debe coincidir con las credenciales de Postgres.

# 3. Comprueba que Docker Desktop o Docker Engine esté iniciado.
# Levanta Postgres en segundo plano. Los datos persisten en el volumen rumbo_pgdata.
docker compose up -d

# 4. Crear/actualizar las tablas y cargar catálogo, fuentes e indicadores.
alembic upgrade head
python -m seeds.load

# 5. Opcional: primera descarga de datos y carga de archivos de analítica.
# Puede tardar porque consulta las fuentes configuradas.
python -m app.jobs.run --all
python -m app.ingestion.load_analytics

# 6. Levanta la API y deja esta terminal abierta.
uvicorn app.main:app --reload --port 8010
```

**Windows (PowerShell):**

Abre PowerShell en la raíz del repositorio y ejecuta los pasos en orden. Los comandos de
migraciones, carga y API deben ejecutarse desde `backend/backend`.

```powershell
# 1. Entra en la carpeta del backend.
Set-Location .\backend\backend

# 2. Crea y activa el entorno virtual.
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"

# 3. Crea .env solo si todavía no existe, para conservar los valores locales.
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
} else {
    Write-Output ".env ya existe; se conserva."
}

# Abre .env y completa los valores antes de iniciar Docker.
# Cambia, como mínimo, POSTGRES_PASSWORD y ADMIN_API_KEY.
# DATABASE_URL debe coincidir con las credenciales de Postgres.
notepad .env

# 4. Abre Docker Desktop y espera a que indique que el motor está iniciado.
# Puedes comprobar la conexión desde PowerShell:
docker info

# 5. Inicia Postgres en segundo plano.
docker compose up -d

# 6. Crea/actualiza las tablas y carga catálogo, fuentes e indicadores.
alembic upgrade head
python -m seeds.load

# 7. Opcional: primera descarga de datos y carga de archivos de analítica.
# Puede tardar porque consulta las fuentes configuradas.
python -m app.jobs.run --all
python -m app.ingestion.load_analytics

# 8. Levanta la API y deja esta terminal abierta.
uvicorn app.main:app --reload --port 8010
```

Si PowerShell no permite activar el entorno virtual, el comando
`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` habilita los scripts
solo en esa ventana de PowerShell; no cambia la política permanente del equipo.

`.env` tiene solo secretos y valores de cada entorno; **no se sube a git**. El resto de la
configuración está en `backend/config/`. Para autenticación local también completa
`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_REDIRECT_URL` y `CORS_ORIGINS` en `backend/.env`;
los valores de ejemplo permiten el frontend en `http://localhost:3010`.

### Docker: detener y volver a iniciar Postgres

El servicio `db` del archivo `backend/backend/docker-compose.yml` usa `postgres:17`, publica el
puerto configurado en `POSTGRES_PORT` (por defecto, `5432`) y guarda la base en el volumen
nombrado `rumbo_pgdata`. Por eso, detener el contenedor no elimina los datos.

Desde `backend/backend`, tanto en Bash como en PowerShell:

```text
docker compose stop       # Detiene Postgres y conserva el contenedor y los datos.
docker compose start      # Vuelve a iniciar el contenedor detenido.
docker compose up -d      # Crea o inicia el servicio en segundo plano.
docker compose logs -f db # Sigue los registros; Ctrl+C sale del seguimiento.
docker compose down       # Elimina el contenedor y la red, pero conserva rumbo_pgdata.
```

Después de reiniciar la computadora, abre Docker Desktop y espera a que el motor esté iniciado.
Desde `backend/backend`, ejecuta `docker compose up -d` y vuelve a levantar la API (paso 6 en Bash
o paso 8 en PowerShell). No hace falta repetir las migraciones ni la carga inicial mientras se
conserve el volumen.

## Explorer

Con la API corriendo, http://localhost:8010/explorer (el Explorer) muestra todo lo que devuelve la API, con datos
en vivo. Es una herramienta de desarrollo y revisión, no el diseño final. Secciones:

- **Indicadores:** serie observada con fuente, tendencia, proyección orientativa y "¿Cómo se calcula?".
- **Ofertas de empleo (LinkedIn):** tarjetas, tabla sector × provincia que filtra al hacer clic,
  total por sector y listado paginado (la misma vista del prototipo en Next.js).
- **Alertas**, con sus reglas.
- **Índice Sintético de Empleabilidad (ISE):** mejores, peores y todas las ocupaciones, orden por
  cualquier dimensión, detalle de cada dimensión y aviso de la dimensión sin fuente (tasa de inserción).
- **Brechas de habilidades** por país (Argentina, Chile y Uruguay).
- **Desajuste educación-ocupación:** sobre y subcalificación, con la tabla de ocupados de la que
  sale cada porcentaje.
- **Correspondencia carrera → ocupación**, para revisarla.
- **Fuentes y archivos oficiales:** estado de las fuentes, archivos leídos y carga manual.

Documentación interactiva de la API: http://localhost:8010/docs · estado: http://localhost:8010/health

## Fuentes de datos

| Fuente | Qué aporta | Cómo se actualiza |
|---|---|---|
| World Bank | Indicadores socioeconómicos y educativos de los 3 países | API, semanal |
| ILOSTAT (OIT) | Desocupación, empleo por sector y ocupación, ingresos, ocupados por ocupación y nivel educativo | API, semanal |
| Datos Argentina (INDEC) | IPC, EMAE, EPH trimestral | API, diaria |
| SIMEL (INE Chile) | Empleo por ocupación de Chile | API, diaria |
| SIPA (Argentina) | Asalariados registrados por rama | Archivo oficial, diaria |
| INE Uruguay | IPC | Archivo oficial, diaria |
| Mi Futuro (MINEDUC, Chile) | Titulados por carrera | Archivo oficial, semanal |
| Indicadores CTI (Argentina) | Egresados universitarios por disciplina | Archivo oficial, semanal |
| MEC Uruguay | Egresados universitarios por carrera (un anuario por año) | Archivo oficial, semanal |
| ESCO (Comisión Europea) | Habilidades por ocupación | API, mensual |
| OIT (2025) | Exposición de las ocupaciones a la IA generativa | Tabla de referencia |
| LinkedIn (Apify) | Ofertas de empleo de Argentina; **no es una fuente oficial** | CSV, a mano |

Los archivos oficiales se descargan solos desde la página oficial, pero **solo se cargan si
mantienen el formato validado**. Si el formato cambió, no se carga nada, se conservan los datos
anteriores y se genera una alerta. Detalle de cada fuente, URL y criterio en
[`docs/fuentes_y_criterios.md`](docs/fuentes_y_criterios.md).

## Configuración: nada hardcodeado

| Dónde | Qué |
|---|---|
| `backend/.env` | Secretos y valores por entorno: `DATABASE_URL`, credenciales de Postgres, `CORS_ORIGINS`, `ADMIN_API_KEY` |
| `config/catalog.yaml` | Países, sectores (CIIU e ILOSTAT), universo de ocupaciones (las 436 de CIUO-08), destacadas, excluidas y reglas de nombres |
| `config/sources.yaml` | Fuentes, URLs, frecuencia y horario de actualización, opciones de cada conector, reintentos HTTP |
| `config/indicators.yaml` | Indicadores y las series de cada fuente que los alimentan |
| `config/datasets/` | Perfiles de archivos oficiales: dónde está cada archivo, cómo leerlo y qué formato debe mantener |
| `config/reference/` | Tablas de referencia: ocupaciones y grupos CIUO-08, exposición a IA, correspondencias carrera → ocupación, niveles educativos por ocupación |
| `config/analytics.yaml` | Metodología: ISE, tendencias, proyecciones, brechas, alertas, recálculo |
| `config/app.yaml` | Paginación, textos y etiquetas de la API y del Explorer, rutas de archivos, mensajes |

Ejemplos:
- **Agregar un indicador:** sumalo a `indicators.yaml`, corré `python -m seeds.load` y
  `python -m app.jobs.run --source <fuente>`. No hace falta tocar código.
- **Cambiar la metodología** (`analytics.yaml`): recalculá sin volver a descargar con
  `python -m app.jobs.recompute`.

## Comandos útiles

Desde `backend/backend`, con el entorno virtual activado:

| Comando | Qué hace |
|---|---|
| `python -m app.jobs.run --all` | Actualiza todas las fuentes con conector (o una: `--source mec_uruguay`) |
| `python -m app.jobs.recompute` | Recalcula tendencias, proyecciones, ISE, brechas y alertas |
| `python -m app.jobs.scheduler` | Actualización automática según los horarios de `sources.yaml` (`--list` muestra los horarios) |
| `python -m app.jobs.validate_crosswalk` | Revisa las correspondencias carrera → ocupación después de editarlas |
| `python -m app.ingestion.load_analytics` | Carga los CSV del equipo de datos (ofertas de LinkedIn, cobertura, egresados) |
| `pytest` · `ruff check .` | Tests y estilo de código |

## Historial: no se borra nada

- **Datos de las fuentes:** si una fuente corrige o deja de publicar un valor ya cargado, el valor
  anterior queda en la tabla `data_revisions` (`GET /api/v1/sources/{fuente}/revisions`).
- **Archivos oficiales:** cada archivo descargado o cargado se guarda con su huella y su reporte de
  validación; el que reemplaza a otro queda marcado, no se borra.
- **Resultados:** los calculados con parámetros anteriores se conservan
  (`analytics.yaml → recompute.keep_superseded_results: true`). La API muestra los vigentes y la
  tabla `methodologies` documenta los parámetros de cada versión.

## Ofertas de LinkedIn (Apify)

1. Exportá cada búsqueda desde la consola de Apify (Storage → Datasets → Export → CSV) y guardala en
   `data/raw/linkedin_jobs/`, sin sobrescribir archivos anteriores. Cada búsqueda es una provincia.
2. Asociá cada archivo a su provincia en `FILE_PROVINCE` de `data/scripts/build_ofertas_linkedin.py`
   y corré `python data/scripts/build_ofertas_linkedin.py`. Escribe
   `data/processed/data_analytics/ofertas_linkedin.csv`, con el sector asignado por reglas.
3. Cargalo con `python -m app.ingestion.load_analytics`.

No guardes el token de Apify en el repositorio ni lo compartas en chats.

## Frontend: dashboard y autenticación

Con la API corriendo en el puerto 8010 y las variables de Supabase configuradas en
`backend/.env` y `frontend/.env.local`:

```bash
cd backend/frontend
npm install
cp .env.example .env.local
npm run dev
```

Abrí http://localhost:3010/auth para iniciar sesión o registrarte; el acceso es opcional.
Después de autenticarte, se abre el Explorer del backend en http://localhost:8010/explorer, donde
se muestran los datos y el correo de la sesión activa y se puede cerrar sesión. Habilita Google en
Supabase y permite `http://localhost:3010/auth/callback` como URL de redirección; ese callback
completa la validación antes de enviar al Explorer. Si vuelves a `/auth` mientras la cookie de sesión
siga activa, se te redirigirá al Explorer en lugar de permitir otro inicio de sesión; cierra sesión
desde el Explorer para volver a autenticarte.

## Estado actual

**Hecho:**
- API con datos oficiales de las fuentes de arriba, actualización automática y control de formato.
- Tendencias, proyecciones orientativas y alertas.
- ISE por ocupación (436 ocupaciones × 3 países).
- Brechas de habilidades de Argentina, Chile y Uruguay.
- Desajuste educación-ocupación.
- Carga manual de archivos e historial de datos.
- Explorer.

**Pendiente:**
- **Data Analytics** ([`docs/pendientes_analytics.md`](docs/pendientes_analytics.md)): revisar las
  tres correspondencias carrera → ocupación y verificar dos cifras del anuario 2024 de Uruguay antes
  de publicar las brechas.
- **Tasa de inserción del ISE:** sin fuente oficial todavía. Hay que enviar el pedido al SIES.
- **Supabase y despliegue:** migración de la base, permisos (RLS) y publicación de la API.
- **Fuentes sin conector:** CEPALSTAT y Banco Central de Chile.

## Problemas frecuentes

- **`Connection refused` al puerto 5432:** Postgres no está corriendo. Abrí Docker Desktop y corré
  `docker compose up -d` en `backend/backend`.
- **`Cannot connect to the Docker daemon`:** Docker Desktop no está abierto.
- **`Field required ... database_url` al iniciar:** falta `backend/backend/.env` (copiá `.env.example`).
- **El puerto 8010 está ocupado:** usá otro puerto y actualizá `NEXT_PUBLIC_API_URL` para que apunte a la API.
- **Windows: no se puede ejecutar `Activate.ps1`:** ejecutá una vez
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **Cambié un YAML y la API no lo toma:** la configuración se lee al arrancar; reiniciá la API.
