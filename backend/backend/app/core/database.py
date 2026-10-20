from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

_connect_args = (
    {"connect_timeout": settings.database_connect_timeout}
    if settings.database_url.startswith("postgresql")
    else {}
)
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_session():
    with SessionLocal() as session:
        yield session
