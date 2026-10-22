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
├── frontend/              primer prototipo en Next.js (puerto 3010)
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

## Puesta en marcha local

La aplicación completa necesita **dos servidores ejecutándose al mismo tiempo**:

1. **Backend Python (FastAPI):** sirve la API y el Explorer en `http://localhost:8010`.
2. **Frontend Next.js:** sirve el dashboard en `http://localhost:3010` y consulta la API.

Abrí **dos terminales** y deja ambas abiertas mientras uses la aplicación. Si una terminal se
cierra o detienes el proceso, ese servidor deja de estar disponible. La base de datos local es
PostgreSQL en Docker; Supabase se usa para autenticación.

### Preparación inicial (una sola vez)

Los siguientes comandos parten de la raíz del repositorio. Usa la sección correspondiente a tu
sistema operativo.

**Windows (PowerShell):**

```powershell
cd backend\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.example .env
```

**macOS / Linux (bash):**

```bash
cd backend/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

En ambos casos, completa `backend/backend/.env` con la configuración de PostgreSQL y Supabase.
Este archivo contiene valores locales y secretos; **no se sube a Git**. Inicia PostgreSQL y carga
la base y los datos iniciales desde la carpeta `backend/backend`:

**Windows (PowerShell):**

```powershell
docker compose up -d
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m seeds.load
.\.venv\Scripts\python.exe -m app.jobs.run --all
.\.venv\Scripts\python.exe -m app.ingestion.load_analytics
```

**macOS / Linux (bash, con `.venv` activado):**

```bash
docker compose up -d
python -m alembic upgrade head
python -m seeds.load
python -m app.jobs.run --all
python -m app.ingestion.load_analytics
```

Instala las dependencias del frontend y copia su archivo de variables desde `backend/frontend`:

**Windows (PowerShell):**

```powershell
cd ..\frontend
npm.cmd install
copy .env.example .env.local
```

**macOS / Linux (bash):**

```bash
cd ../frontend
npm install
cp .env.example .env.local
```

En `backend/frontend/.env.local`, completa `NEXT_PUBLIC_SUPABASE_URL` y
`NEXT_PUBLIC_SUPABASE_ANON_KEY` con la URL del proyecto Supabase y su clave pública anon/publishable.
`NEXT_PUBLIC_API_URL` debe apuntar a `http://localhost:8010`. El `.env.local` está excluido de Git.

### Inicio diario

Abre **dos terminales** desde la raíz del repositorio. Inicia primero el backend y deja ambos
procesos ejecutándose mientras uses la aplicación.

**Terminal 1 — Backend Python / FastAPI**

Windows (PowerShell):

```powershell
cd backend\backend
docker compose up -d
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8010
```

macOS / Linux (bash):

```bash
cd backend/backend
docker compose up -d
source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8010
```

La API está en `http://localhost:8010`; su documentación en `http://localhost:8010/docs` y el
Explorer en `http://localhost:8010/explorer`.

**Terminal 2 — Frontend Next.js**

Windows (PowerShell):

```powershell
cd backend\frontend
npm.cmd run dev
```

macOS / Linux (bash):

```bash
cd backend/frontend
npm run dev
```

Abre `http://localhost:3010`. Para probar el acceso, visita `http://localhost:3010/auth`.
**El frontend depende de la API; inicia primero la Terminal 1.** Si modificas `.env.local`, reinicia
el servidor de Next.js para que cargue los nuevos valores.

Después de reiniciar la computadora, vuelve a iniciar PostgreSQL, la API en la Terminal 1 y Next.js
en la Terminal 2. No es necesario repetir la carga inicial de datos.

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

## Prototipo en Next.js (frontend)

Con la API corriendo en el puerto 8010:

```bash
cd backend/frontend
npm install
cp .env.example .env.local     # NEXT_PUBLIC_API_URL=http://localhost:8010
npm run dev
```

Abrí http://localhost:3010. Fue la primera vista (ofertas de LinkedIn, egresados y cobertura); el
Explorer ya incluye la misma vista de ofertas.

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
- **El puerto 8010 está ocupado:** usá otro, por ejemplo `--port 8011`.
- **Windows: no se puede ejecutar `Activate.ps1`:** ejecutá una vez
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **Cambié un YAML y la API no lo toma:** la configuración se lee al arrancar; reiniciá la API.
