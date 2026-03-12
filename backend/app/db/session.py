r"""
Purpose: Database engine and session management for PostgreSQL-compatible access.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\db\session.py
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session for a request lifecycle."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
