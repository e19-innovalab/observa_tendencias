from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.v1 import (
    alerts,
    catalog,
    coverage,
    datasets,
    employability,
    graduates,
    indicators,
    jobs,
    skills,
    sources,
    trends,
)
from app.core.config import settings

app = FastAPI(title=f"{settings.app_name} API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

for module in (catalog, indicators, employability, trends, skills, alerts, datasets, sources,
               coverage, jobs, graduates):
    app.include_router(module.router, prefix="/api/v1")


@app.exception_handler(OperationalError)
def database_unavailable(request: Request, exc: OperationalError):
    return JSONResponse(
        status_code=503,
        content={"detail": "No se pudo conectar a la base de datos. Revisá DATABASE_URL en backend/.env"},
    )


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
