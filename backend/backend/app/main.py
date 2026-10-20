from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.v1 import (
    alerts,
    catalog,
    coverage,
    datasets,
    education,
    employability,
    graduates,
    indicators,
    jobs,
    skills,
    sources,
    trends,
)
from app.core.config import BACKEND_DIR, settings
from app.core.config_files import app_config

conf = app_config()
app = FastAPI(title=f"{conf.app_name} API", version=conf.version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=conf.cors.allow_methods,
    allow_headers=conf.cors.allow_headers,
)

for module in (catalog, indicators, employability, trends, skills, alerts, datasets, sources,
               coverage, jobs, graduates, education):
    app.include_router(module.router, prefix=conf.api_prefix)


@app.exception_handler(OperationalError)
def database_unavailable(request: Request, exc: OperationalError):
    return JSONResponse(status_code=503, content={"detail": conf.messages["db_unavailable"]})


if conf.dev_tools.explorer:
    @app.get("/explorer", include_in_schema=False)
    def explorer():
        return FileResponse(BACKEND_DIR / "app" / "static" / "explorer.html")


@app.get("/health")
def health():
    return {"status": "ok", "app": conf.app_name}
