# Rumbo: backend

FastAPI + PostgreSQL (Supabase). La estructura sigue `backend_plan_ES.md`.

Las instrucciones completas de instalación y puesta en marcha están en
[`../README.md`](../README.md).

Resumen (desde esta carpeta, con el entorno virtual activo):

```powershell
pip install -e ".[dev]"
copy .env.example .env           # completar DATABASE_URL
alembic upgrade head
python -m seeds.load
uvicorn app.main:app --reload    # http://localhost:8000/docs
pytest
```

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
