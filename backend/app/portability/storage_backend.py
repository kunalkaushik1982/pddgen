r"""
Select `StorageBackend` from settings so object storage vs local is decided in one place.

Add new backends by extending this function and implementing `StorageBackend` in
`app.storage.storage_service` (or a plugin module that returns a compatible backend).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import Settings

if TYPE_CHECKING:
    from app.storage.storage_service import StorageBackend


def select_storage_backend(settings: Settings) -> StorageBackend:
    """Return the configured storage backend implementation."""
    from app.storage.storage_service import LocalStorageBackend, S3CompatibleStorageBackend, StorageBackend

    backend_name = settings.storage_backend.lower()
    if backend_name == "local":
        return LocalStorageBackend(settings)
    if backend_name in {"s3", "r2"}:
        return S3CompatibleStorageBackend(settings)
    raise RuntimeError(f"Unsupported storage backend: {settings.storage_backend}")
