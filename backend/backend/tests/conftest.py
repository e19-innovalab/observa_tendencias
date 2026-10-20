import os

# Tests never touch the real database: endpoints get an in-memory SQLite session.
os.environ.setdefault("DATABASE_URL", "sqlite://")

# Tables SQLite cannot create (PostgreSQL ARRAY columns); nothing in the tests needs them.
SQLITE_UNSUPPORTED = {"sectors"}


def sqlite_tables():
    """Every model table the in-memory test databases can create."""
    from app.models import Base

    return [t for name, t in Base.metadata.tables.items() if name not in SQLITE_UNSUPPORTED]
