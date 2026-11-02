# Observa Tendencias: backend

FastAPI + PostgreSQL (Supabase). La estructura sigue `backend_plan_ES.md`.

Las instrucciones completas de instalación y puesta en marcha están en
[`../README.md`](../README.md).

Resumen (desde esta carpeta, con el entorno virtual activo):

```powershell
pip install -e ".[dev]"
copy .env.example .env           # completar DATABASE_URL y AUTH_SECRET
docker compose up -d             # Postgres local
alembic upgrade head
python -m seeds.load
python -m app.jobs.create_user   # usuario para entrar a los frontends
uvicorn app.main:app --reload --port 8010    # http://localhost:8010/docs
pytest
```

## Estructura del proyecto

```
backend/
├── app/
│   ├── main.py              # punto de entrada FastAPI
│   ├── api/v1/              # routers: catálogo, indicadores, ISE, habilidades y brechas,
│   │                        #   alertas, fuentes, carga de archivos (datasets), usuarios y
│   │                        #   sesión, asistente, y los índices de cada módulo
│   ├── assistant/           # asistente: plantillas de respuesta, herramientas (endpoints de
│   │                        #   lectura), proveedores de modelo, chequeo de números
│   ├── core/                # configuración (.env y YAML), base, sesión, búsqueda de texto
│   ├── models/              # modelos SQLAlchemy (catálogo, fuentes, cálculos, usuarios, asistente)
│   ├── schemas/             # esquemas de respuesta de la API
│   ├── connectors/          # conectores a fuentes externas
│   ├── datasets/            # archivos oficiales y carga manual: perfiles, control del archivo,
│   │                        #   lectura, validación y carga
│   ├── ingestion/           # pipeline de actualización, historial de revisiones, CSV del equipo
│   ├── normalization/       # correspondencias, períodos, unidades
│   ├── analytics/           # tendencias, proyecciones, ISE, brechas, alertas, recálculo e
│   │                        #   indicadores temáticos (Moctezuma, Ludita, Reina Roja, Sísifo)
│   ├── skills/              # ESCO: habilidades por ocupación y su jerarquía; versiones de
│   │                        #   ESCO y O*NET (Reina Roja)
│   ├── jobs/                # tareas de consola: run, recompute, scheduler, create_user…
│   ├── services/            # lógica compartida (observaciones, usuarios)
│   └── static/              # Explorer (herramienta de revisión)
├── config/                  # toda la configuración (YAML) y tablas de referencia
├── migrations/              # Alembic
├── seeds/                   # carga del catálogo, fuentes e indicadores desde config/
├── tests/                   # tests (base SQLite en memoria; no necesitan Postgres)
├── ml/occupation_match/     # prototipo: búsqueda de ocupaciones por significado
├── alembic.ini
├── pyproject.toml
├── .env.example
└── backend_plan_ES.md       # plan de arquitectura original
```
