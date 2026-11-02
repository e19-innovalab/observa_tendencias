# Observa Tendencias · Observatorio de tendencias laborales y educativas

Observatorio predictivo de tendencias laborales y educativas del Cono Sur (Argentina, Uruguay y
Chile), del programa InnovaLab. Junta datos oficiales de empleo, salarios, educación y formación,
calcula tendencias, proyecciones, un Índice Sintético de Empleabilidad (ISE) por ocupación,
brechas de habilidades, alertas e indicadores temáticos (Moctezuma, Ludita, Reina Roja, Sísifo y
Brecha generacional), y los expone en una API.

## Estructura

```
backend/                   (esta carpeta)
├── backend/               API en FastAPI + PostgreSQL
│   ├── app/               código: conectores, lectura de archivos oficiales, cálculos, API
│   ├── config/            toda la configuración (YAML): fuentes, indicadores, metodología, textos
│   ├── migrations/        migraciones de la base (Alembic)
│   ├── seeds/             carga del catálogo, fuentes e indicadores desde config/
│   ├── tests/             tests (no necesitan base de datos)
│   ├── ml/                prototipos de modelos (búsqueda de ocupaciones por significado)
│   └── docker-compose.yml Postgres local
├── frontend/              primer prototipo en Next.js (puerto 3010)
├── frontend_minimal/     frontend minimal en Next.js (puerto 3001): el que se publica en Vercel
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
| [`docs/fuentes_y_criterios.md`](docs/fuentes_y_criterios.md) | Fuentes, URLs, indicadores y criterios de cálculo: tendencias, proyecciones, ISE, brechas de habilidades, desajuste educación-ocupación, indicadores temáticos, alertas e historial de datos |
| [`docs/guia_api_frontend.md`](docs/guia_api_frontend.md) | Qué endpoint alimenta cada pantalla del mockup |
| [`docs/pendientes_analytics.md`](docs/pendientes_analytics.md) | Revisiones y decisiones pendientes del equipo de Data Analytics |
| [`data/scripts/referencias/README.md`](data/scripts/referencias/README.md) | Ocupaciones CIUO-08, correspondencias carrera → ocupación de los tres países y los scripts que las generan |
| [`docs/solicitud_sies_empleabilidad.md`](docs/solicitud_sies_empleabilidad.md) | Pedido al SIES (Chile) de la base de empleabilidad por carrera, para la tasa de inserción del ISE |
| [`docs/despliegue.md`](docs/despliegue.md) | Cómo publicar en la nube: base en Supabase, API en Render, frontend en Vercel |
| [`docs/conexion_supabase.md`](docs/conexion_supabase.md) | Cómo conectar a Supabase (para cuando se migre) |
| [`backend/backend_plan_ES.md`](backend/backend_plan_ES.md) | Plan completo del backend |
| [`backend/ml/occupation_match/README.md`](backend/ml/occupation_match/README.md) | Prototipo de búsqueda de ocupaciones por significado: datos, evaluación y cómo entrenar en otra máquina |
| [`backend/config/datasets/ejemplos/README.md`](backend/config/datasets/ejemplos/README.md) | Archivos de ejemplo para probar la carga manual |
| [`frontend_minimal/README.md`](frontend_minimal/README.md) | Frontend minimal (pantallas, buscador, asistente, carga de datos) |

## Requisitos

- Python 3.11 o superior
- Docker Desktop (para la base PostgreSQL local)
- Git
- Node.js 18.18 o superior, solo para los frontends en Next.js
- Opcional, para el asistente: [Ollama](https://ollama.com) con un modelo abierto, o una clave de la API de Anthropic (ver "Asistente")

## Puesta en marcha

Hoy se trabaja con una base **PostgreSQL local** en Docker (versión 17, la misma que Supabase).
Pasar a Supabase más adelante solo requiere cambiar `DATABASE_URL` en `.env`.

**macOS / Linux:**

```bash
cd backend/backend

# 1. Entorno virtual y dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Variables de entorno: copiar y completar (cambiá la clave de Postgres y ADMIN_API_KEY)
cp .env.example .env

# 3. Levantar Postgres (los datos quedan en el volumen rumbo_pgdata)
docker compose up -d

# 4. Crear las tablas y cargar catálogo, fuentes e indicadores desde config/*.yaml
alembic upgrade head
python -m seeds.load

# 5. Traer los datos de todas las fuentes con conector y cargar los CSV del equipo de datos
python -m app.jobs.run --all
python -m app.ingestion.load_analytics

# 6. Levantar la API
uvicorn app.main:app --reload --port 8010
```

**Windows (PowerShell):** los mismos pasos, con `python -m venv .venv`,
`.venv\Scripts\Activate.ps1` y `copy .env.example .env`.

`.env` tiene solo secretos y valores de cada entorno; **no se sube a git**. El resto de la
configuración está en `backend/config/`.

Después de reiniciar la computadora: abrí Docker Desktop, corré `docker compose up -d` y volvé a
levantar la API (paso 6).

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
| ESCO, por versión | Habilidades de cada ocupación en cada versión (indicador Reina Roja) | API, anual |
| O*NET (EE. UU.) | Tecnologías de cada ocupación en cada versión (indicador Reina Roja) | Archivo oficial, anual |
| OIT (2025) | Exposición de las ocupaciones a la IA generativa | Tabla de referencia |
| LinkedIn (Apify) | Ofertas de empleo de Argentina; **no es una fuente oficial** | CSV, a mano |

Los archivos oficiales se descargan solos desde la página oficial, pero **solo se cargan si
mantienen el formato validado**. Si el formato cambió, no se carga nada, se conservan los datos
anteriores y se genera una alerta. Detalle de cada fuente, URL y criterio en
[`docs/fuentes_y_criterios.md`](docs/fuentes_y_criterios.md).

## Configuración: nada hardcodeado

| Dónde | Qué |
|---|---|
| `backend/.env` | Secretos y valores por entorno: `DATABASE_URL`, credenciales de Postgres, `CORS_ORIGINS`, `ADMIN_API_KEY`, `AUTH_SECRET` (inicio de sesión), `ANTHROPIC_API_KEY` y `ASSISTANT_LOCAL_API_KEY` (asistente, solo la del proveedor elegido) |
| `config/catalog.yaml` | Países, sectores (CIIU e ILOSTAT), universo de ocupaciones (las 436 de CIUO-08), destacadas, excluidas y reglas de nombres |
| `config/sources.yaml` | Fuentes, URLs, frecuencia y horario de actualización, opciones de cada conector, reintentos HTTP |
| `config/indicators.yaml` | Indicadores y las series de cada fuente que los alimentan |
| `config/datasets/` | Perfiles de archivos oficiales: dónde está cada archivo, cómo leerlo y qué formato debe mantener. En `ejemplos/`, archivos para probar la carga manual |
| `config/reference/` | Tablas de referencia: ocupaciones y grupos CIUO-08, campos CINE-F 2013 y su tabla campo → ocupación, carreras de cada país con su campo, exposición a IA, niveles educativos por ocupación, nombres locales de ocupaciones |
| `config/analytics.yaml` | Metodología: ISE, tendencias, proyecciones, brechas, alertas, recálculo |
| `config/app.yaml` | Paginación, textos y etiquetas de la API y del Explorer, rutas de archivos, mensajes, búsqueda, carga manual (límites, plantilla, mensajes), asistente (modelo, herramientas, plantillas de respuesta, límites, instrucciones) |

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
| `python -m app.jobs.create_user` | Crea un usuario (para entrar a los frontends) |
| `ollama serve` · `ollama pull qwen2.5:7b-instruct` | Modelo local del asistente (solo si se usa `provider: local`) |
| `pytest` · `ruff check .` | Tests y estilo de código |

## Historial: no se borra nada

- **Datos de las fuentes:** si una fuente corrige o deja de publicar un valor ya cargado, el valor
  anterior queda en la tabla `data_revisions` (`GET /api/v1/sources/{fuente}/revisions`).
- **Archivos oficiales:** cada archivo descargado o cargado se guarda con su huella y su reporte de
  validación; el que reemplaza a otro queda marcado, no se borra.
- **Resultados:** los calculados con parámetros anteriores se conservan
  (`analytics.yaml → recompute.keep_superseded_results: true`). La API muestra los vigentes y la
  tabla `methodologies` documenta los parámetros de cada versión.
- **Asistente:** cada pregunta queda en `assistant_logs` con la respuesta, las consultas que hizo,
  los números que no pudo verificar, los tokens y el tiempo.

## Asistente ("Preguntale al Observatorio")

Responde preguntas con los datos del observatorio (`POST /api/v1/assistant/ask`, con sesión). Solo
puede consultar endpoints de lectura de la API, listados en `config/app.yaml → assistant.tools`.
Revisa que cada número de la respuesta aparezca en los datos que consultó y devuelve enlaces a las
páginas con esos datos. Todo se configura en `app.yaml → assistant`: modelo, límites por día,
instrucciones y textos.

**Con un modelo abierto en tu máquina** (`provider: local`, el valor por defecto; funciona en CPU):

1. Instalá [Ollama](https://ollama.com) y descargá el modelo de `assistant.providers.local.model`:
   `ollama pull qwen2.5:7b-instruct` (unos 5 GB).
2. Dejá Ollama abierto; escucha en `http://localhost:11434`.
3. En un servidor sin Ollama sirve también `llama-server` (llama.cpp) con un archivo GGUF: cambiá
   `base_url` a `http://localhost:8080/v1`.

**Con Claude** (`provider: anthropic`): poné `ANTHROPIC_API_KEY` en `backend/.env` y cambiá
`assistant.provider`.

**Respuestas por plantilla (sin modelo).** Las preguntas frecuentes se responden al instante con
plantillas y los datos de la API (`app.yaml → assistant.scripted`):
- salario, empleabilidad y habilidades de una ocupación;
- ranking y sectores de un país;
- cómo se calcula el ISE.

Reconoce la ocupación por código, nombre o nombre local, y el país por su nombre o la página que
se está mirando. Si hay varias ocupaciones posibles, ofrece botones para elegir. Solo lo demás va
al modelo, y solo eso cuenta para el límite diario.

**Nombres locales.** `config/reference/ocupaciones_nombres_locales.yaml` (revisado contra ISCO-08)
tiene palabras de Argentina, Chile y Uruguay con su código CIUO: remisero, gasfíter, colectivero…
Los usan el buscador (`/occupations?q=remisero` encuentra 8322) y el asistente. El buscador además
ignora tildes, orden de las palabras, plural y género ("enfermera" encuentra "enfermería").

**Detener.** Si quien pregunta corta la pregunta, el backend detiene el modelo y la pregunta no
cuenta para el límite.

Sin modelo disponible, las preguntas que necesitan modelo reciben `503` con un aviso; las
plantillas siguen funcionando y el resto de la app no se ve afectada.
`assistant.enabled: false` lo apaga.

## Carga manual de datos

En los frontends: menú de la cuenta → **Carga de datos** (solo roles con permiso `manage_data`).
En la API: `POST /api/v1/datasets/upload` y después `POST /api/v1/datasets/{id}/commit`.

1. **Elegir el formato.** Puede ser uno de los archivos oficiales que la plataforma sabe leer, o
   la **plantilla genérica**: una fila por valor, con `indicador, pais, periodo, frecuencia, valor`
   y, opcionales, `sector` y `ocupacion`. La plantilla se baja desde la misma pantalla, en Excel
   con hojas de códigos válidos o en CSV, y hay dos archivos de ejemplo para probar.
2. **Subir y revisar.** Nada se carga todavía. Primero se revisa que el archivo sea lo que dice:
   - un `.xlsx` real y sin macros, o un CSV de texto en UTF-8;
   - dentro de los límites de tamaño y de filas.

   Después se valida cada fila contra el catálogo. Los errores se muestran agrupados, con las
   filas, los valores y qué hacer. Por ejemplo: "Países fuera del catálogo: 2 filas (2, 9) ·
   «BRA», «PER» — Usá ARG, CHL o URY".
3. **Confirmar.** Si el archivo repite valores que ya publicó una fuente oficial, avisa y pide
   confirmación. Los valores se guardan como fuente aparte y no reemplazan el dato oficial. Al
   cargar se recalculan tendencias, proyecciones, ISE y alertas.

Cada archivo, aceptado o rechazado, queda en el historial con su motivo. Límites, mensajes y
plantilla se configuran en `app.yaml → datasets`.

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
- Brechas de habilidades de Argentina, Chile y Uruguay, con las carreras clasificadas por la CINE-F 2013 (UNESCO).
  La versión anterior, con correspondencias directas por país, está marcada como `v0.1`.
- Desajuste educación-ocupación.
- Indicadores temáticos: Moctezuma, Ludita, Reina Roja, Sísifo, Brecha generacional y las
  burbujas de Tendencias (sección 7 de [`docs/fuentes_y_criterios.md`](docs/fuentes_y_criterios.md)).
- Carga manual de archivos: plantilla descargable, control del archivo real, errores agrupados y
  aviso de choque con datos oficiales. Historial de datos.
- Inicio de sesión con roles (administrador, editor, consultas).
- Asistente "Baqueano": respuestas por plantilla para las preguntas frecuentes y modelo abierto
  local (o Claude) para el resto, con chequeo de números, límites diarios y registro.
- Buscador tolerante: tildes, orden, plural y género, y nombres locales de ocupaciones.
- Explorer.

**Pendiente:**
- **Data Analytics** ([`docs/pendientes_analytics.md`](docs/pendientes_analytics.md)): revisar las
  tres correspondencias carrera → ocupación y verificar dos cifras del anuario 2024 de Uruguay antes
  de publicar las brechas.
- **Tasa de inserción del ISE:** sin fuente oficial todavía. Hay que enviar el pedido al SIES.
- **Supabase y despliegue:** en curso, siguiendo [`docs/despliegue.md`](docs/despliegue.md). Ya se reactivó el proyecto de Supabase; faltan cargar la base en la nube, subir el código y crear los servicios en Render y Vercel.
- **Fuentes sin conector:** CEPALSTAT y Banco Central de Chile.
- **Asistente:** el modelo local de 7B a veces no completa el segundo paso (buscar y después
  consultar), y el chequeo de números bloquea esas respuestas. Falta comparar con un modelo más
  grande o con Claude, y decidir cuál usar.
- **Búsqueda por significado:** entrenar el modelo del prototipo (`backend/ml/occupation_match/`)
  y conectarlo al buscador y al asistente.
- **Carga manual, segunda etapa:** retirar una carga sin borrarla y marcar en las pantallas los
  datos que vienen de carga manual.
- **Migraciones:** `0024_assistant_logs` se creó en paralelo con otras sesiones de trabajo; revisar
  la numeración antes de unir las ramas.

## Problemas frecuentes

- **`Connection refused` al puerto 5432:** Postgres no está corriendo. Abrí Docker Desktop y corré
  `docker compose up -d` en `backend/backend`.
- **`Cannot connect to the Docker daemon`:** Docker Desktop no está abierto.
- **`Field required ... database_url` al iniciar:** falta `backend/backend/.env` (copiá `.env.example`).
- **El puerto 8010 está ocupado:** usá otro, por ejemplo `--port 8011`.
- **Windows: no se puede ejecutar `Activate.ps1`:** ejecutá una vez
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **Cambié un YAML y la API no lo toma:** la configuración se lee al arrancar; reiniciá la API.
- **El asistente responde "no responde en este momento" (503):** el modelo no está disponible. Con
  `provider: local`, abrí Ollama (`ollama serve`) y verificá que el modelo de
  `assistant.providers.local.model` esté descargado (`ollama list`). Las respuestas por plantilla
  siguen funcionando igual.
- **La pestaña del asistente no aparece:** `assistant.enabled` está en `false` o el frontend no
  llega al backend.
