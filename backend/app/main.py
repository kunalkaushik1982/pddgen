r"""
Purpose: FastAPI application entry point for the backend service.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\main.py
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, draft_sessions, exports, meta, uploads
from app.core.config import get_settings
from app.db.schema_validation import validate_database_schema
from app.middleware.csrf import CSRFMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize application resources on startup."""
    settings = get_settings()
    settings.local_storage_root.mkdir(parents=True, exist_ok=True)
    validate_database_schema()
    yield


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
    app.include_router(meta.router, prefix=settings.api_prefix)
    app.include_router(draft_sessions.router, prefix=settings.api_prefix)
    app.include_router(exports.router, prefix=settings.api_prefix)
    return app


app = create_app()
