r"""
Purpose: FastAPI application entry point for the backend service.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\main.py
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, billing_admin, draft_sessions, exports, meetings, meta, metrics, payments, uploads
from app.core.config import get_settings
from app.core.observability import configure_logging, get_logger
from app.db.schema_validation import validate_database_schema
from app.middleware.csrf import CSRFMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.services.platform.csrf_service import CsrfService


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize application resources on startup."""
    settings = get_settings()
    if settings.storage_backend.lower() == "local":
        settings.local_storage_root.mkdir(parents=True, exist_ok=True)
    validate_database_schema()
    logger.info("Backend startup validation complete", extra={"event": "app.startup"})
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    app.state.csrf_service = CsrfService(settings=settings)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(uploads.router, prefix=settings.api_prefix)
    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(admin.router, prefix=settings.api_prefix)
    app.include_router(billing_admin.router, prefix=settings.api_prefix)
    app.include_router(metrics.router, prefix=settings.api_prefix)
    app.include_router(payments.router, prefix=settings.api_prefix)
    app.include_router(meta.router, prefix=settings.api_prefix)
    app.include_router(meetings.router, prefix=settings.api_prefix)
    app.include_router(draft_sessions.router, prefix=settings.api_prefix)
    app.include_router(exports.router, prefix=settings.api_prefix)
    return app


app = create_app()
