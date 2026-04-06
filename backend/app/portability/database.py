r"""
SQLAlchemy engine factory for portable database URLs.

Switch databases by changing `PDD_GENERATOR_DATABASE_URL` (or `database_url` in Settings)
to any SQLAlchemy-supported scheme, for example:

- postgresql+psycopg://...
- mysql+pymysql://...
- mssql+pyodbc://...

Keep Alembic migrations portable (avoid dialect-specific DDL) when targeting multiple engines.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import Settings

# Documented for operators; not enforced at runtime beyond SQLAlchemy's own URL parsing.
SUPPORTED_DATABASE_URL_PREFIXES: tuple[str, ...] = (
    "postgresql",
    "mysql",
    "mssql",
    "sqlite",
)


def build_sqlalchemy_engine(settings: Settings) -> Engine:
    """Create a SQLAlchemy engine from application settings."""
    return create_engine(
        settings.database_url,
        future=True,
        pool_pre_ping=settings.database_pool_pre_ping,
    )
