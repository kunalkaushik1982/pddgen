r"""
Purpose: FastAPI application entry point for the backend service.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\main.py
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.routes import auth, draft_sessions, exports, uploads
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.middleware.csrf import CSRFMiddleware
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize application resources on startup."""
    settings = get_settings()
    settings.local_storage_root.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _ensure_process_step_columns()
    yield


def _ensure_process_step_columns() -> None:
    """Backfill newly added columns for an existing pilot database."""
    inspector = inspect(engine)
    table_updates = {
        "process_steps": {
            "start_timestamp": "ALTER TABLE process_steps ADD COLUMN start_timestamp VARCHAR(50) DEFAULT ''",
            "end_timestamp": "ALTER TABLE process_steps ADD COLUMN end_timestamp VARCHAR(50) DEFAULT ''",
            "supporting_transcript_text": "ALTER TABLE process_steps ADD COLUMN supporting_transcript_text TEXT DEFAULT ''",
        },
        "draft_sessions": {
            "diagram_type": "ALTER TABLE draft_sessions ADD COLUMN diagram_type VARCHAR(50) DEFAULT 'flowchart'",
            "overview_diagram_json": "ALTER TABLE draft_sessions ADD COLUMN overview_diagram_json TEXT DEFAULT ''",
            "detailed_diagram_json": "ALTER TABLE draft_sessions ADD COLUMN detailed_diagram_json TEXT DEFAULT ''",
        },
    }

    with engine.begin() as connection:
        for table_name, expected_columns in table_updates.items():
            try:
                existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            except Exception:
                continue

            missing_statements = [
                statement for column_name, statement in expected_columns.items() if column_name not in existing_columns
            ]
            for statement in missing_statements:
                connection.execute(text(statement))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CSRFMiddleware)

    app.include_router(uploads.router, prefix=settings.api_prefix)
    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(draft_sessions.router, prefix=settings.api_prefix)
    app.include_router(exports.router, prefix=settings.api_prefix)
    return app


app = create_app()
