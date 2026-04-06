r"""
Portability layer: swap databases, auth providers, queues, and HTTP clients via
configuration and optional extension modules — without changing business rules in
domain services.

See `app.portability.database`, `app.portability.auth_registry`,
`app.portability.celery_job_queue`, `app.portability.storage_backend`,
`app.portability.http_client`.
"""

from app.portability.auth_registry import (
    ExtensibleAuthProviderRegistry,
    build_auth_provider_registry,
)
from app.portability.database import build_sqlalchemy_engine
from app.portability.storage_backend import select_storage_backend

__all__ = [
    "ExtensibleAuthProviderRegistry",
    "build_auth_provider_registry",
    "build_sqlalchemy_engine",
    "select_storage_backend",
]
