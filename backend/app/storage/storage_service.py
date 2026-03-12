r"""
Purpose: Storage abstraction for pilot local storage and future shared or object storage.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\storage\storage_service.py
"""

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings, get_settings


class StorageBackend(Protocol):
    """Contract for artifact and export storage implementations."""

    def save_upload(self, session_id: str, upload: UploadFile, artifact_kind: str) -> tuple[str, int]:
        """Save an uploaded file and return its storage path and byte size."""

    def save_bytes(self, session_id: str, folder: str, filename: str, content: bytes) -> str:
        """Persist generated content and return its storage path."""

    def read_text(self, storage_path: str) -> str:
        """Read stored text content."""

    def ensure_paths(self, paths: Iterable[Path]) -> None:
        """Ensure required directories exist."""


class LocalStorageBackend:
    """Local filesystem implementation for pilot deployments."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def save_upload(self, session_id: str, upload: UploadFile, artifact_kind: str) -> tuple[str, int]:
        target_dir = self.settings.local_storage_root / session_id / artifact_kind
        target_dir.mkdir(parents=True, exist_ok=True)
        target_name = f"{uuid4()}_{upload.filename or 'artifact'}"
        target_path = target_dir / target_name

        content = upload.file.read()
        target_path.write_bytes(content)
        return str(target_path), len(content)

    def save_bytes(self, session_id: str, folder: str, filename: str, content: bytes) -> str:
        target_dir = self.settings.local_storage_root / session_id / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        target_path.write_bytes(content)
        return str(target_path)

    def read_text(self, storage_path: str) -> str:
        return Path(storage_path).read_text(encoding="utf-8", errors="ignore")

    def ensure_paths(self, paths: Iterable[Path]) -> None:
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)


class StorageService:
    """Facade around the configured storage backend."""

    def __init__(self, backend: StorageBackend | None = None) -> None:
        self.backend = backend or LocalStorageBackend()

    def save_upload(self, session_id: str, upload: UploadFile, artifact_kind: str) -> tuple[str, int]:
        """Save an uploaded artifact."""
        return self.backend.save_upload(session_id=session_id, upload=upload, artifact_kind=artifact_kind)

    def save_bytes(self, session_id: str, folder: str, filename: str, content: bytes) -> str:
        """Save generated content."""
        return self.backend.save_bytes(session_id=session_id, folder=folder, filename=filename, content=content)

    def read_text(self, storage_path: str) -> str:
        """Read stored text content."""
        return self.backend.read_text(storage_path)
