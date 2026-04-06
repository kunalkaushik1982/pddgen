r"""
Purpose: Storage abstraction for local and object-backed artifact persistence.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\storage\storage_service.py
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
from pathlib import Path
from typing import Protocol
from urllib.parse import quote
from uuid import uuid4

import boto3
from botocore.client import Config as BotoConfig
from fastapi import UploadFile

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class PreviewDescriptor:
    """Resolvable preview URL metadata for one stored artifact."""

    url: str
    expires_at: datetime | None = None


class StorageBackend(Protocol):
    """Contract for artifact and export storage implementations."""

    def save_upload(self, session_id: str, upload: UploadFile, artifact_kind: str) -> tuple[str, int]:
        """Save an uploaded file and return its storage locator and byte size."""

    def save_bytes(self, session_id: str, folder: str, filename: str, content: bytes) -> str:
        """Persist generated content and return its storage locator."""

    def save_file(self, session_id: str, folder: str, filename: str, source_path: Path) -> str:
        """Persist one local file and return its storage locator."""

    def read_text(self, storage_path: str) -> str:
        """Read stored text content."""

    def read_bytes(self, storage_path: str) -> bytes:
        """Read stored binary content."""

    def copy_to_local_path(self, storage_path: str, target_path: Path) -> Path:
        """Materialize one stored object to a local file path."""

    def ensure_paths(self, paths: Iterable[Path]) -> None:
        """Ensure required directories exist."""

    def delete(self, storage_path: str) -> None:
        """Delete one stored object if it exists."""


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

    def save_file(self, session_id: str, folder: str, filename: str, source_path: Path) -> str:
        return self.save_bytes(session_id=session_id, folder=folder, filename=filename, content=source_path.read_bytes())

    def read_text(self, storage_path: str) -> str:
        return Path(storage_path).read_text(encoding="utf-8", errors="ignore")

    def read_bytes(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    def copy_to_local_path(self, storage_path: str, target_path: Path) -> Path:
        source_path = Path(storage_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve() != target_path.resolve():
            target_path.write_bytes(source_path.read_bytes())
        return target_path if target_path.exists() else source_path

    def ensure_paths(self, paths: Iterable[Path]) -> None:
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)

    def delete(self, storage_path: str) -> None:
        target_path = Path(storage_path)
        if target_path.exists():
            target_path.unlink()

    def build_preview_descriptor(self, artifact: object, settings: Settings) -> PreviewDescriptor:
        expires_at = datetime.now(UTC) + timedelta(seconds=settings.preview_url_ttl_seconds)
        expires = int(expires_at.timestamp())
        signature = _sign_preview_token(
            artifact_id=str(getattr(artifact, "id")),
            expires=expires,
            secret=settings.preview_url_signing_secret,
        )
        filename = quote(str(getattr(artifact, "name", "artifact")))
        return PreviewDescriptor(
            url=(
                f"{settings.api_prefix}/uploads/artifacts/{getattr(artifact, 'id')}/preview"
                f"?expires={expires}&sig={signature}&filename={filename}"
            ),
            expires_at=expires_at,
        )


class S3CompatibleStorageBackend:
    """S3-compatible object storage backend suitable for S3 or Cloudflare R2."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.object_storage_bucket:
            raise RuntimeError("Object storage bucket is required when storage_backend is set to s3 or r2.")
        self.bucket = self.settings.object_storage_bucket
        self.prefix = self.settings.object_storage_prefix.strip("/")
        self.client = boto3.client(
            "s3",
            endpoint_url=self.settings.object_storage_endpoint_url or None,
            region_name=self.settings.object_storage_region or None,
            aws_access_key_id=self.settings.object_storage_access_key_id or None,
            aws_secret_access_key=self.settings.object_storage_secret_access_key or None,
            config=BotoConfig(s3={"addressing_style": self.settings.object_storage_addressing_style}),
        )

    def save_upload(self, session_id: str, upload: UploadFile, artifact_kind: str) -> tuple[str, int]:
        content = upload.file.read()
        target_name = f"{uuid4()}_{upload.filename or 'artifact'}"
        key = self._build_key(session_id=session_id, folder=artifact_kind, filename=target_name)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=upload.content_type or "application/octet-stream",
        )
        return self._to_storage_uri(key), len(content)

    def save_bytes(self, session_id: str, folder: str, filename: str, content: bytes) -> str:
        key = self._build_key(session_id=session_id, folder=folder, filename=filename)
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content)
        return self._to_storage_uri(key)

    def save_file(self, session_id: str, folder: str, filename: str, source_path: Path) -> str:
        key = self._build_key(session_id=session_id, folder=folder, filename=filename)
        extra_args = {}
        content_type = _guess_content_type(source_path)
        if content_type:
            extra_args["ExtraArgs"] = {"ContentType": content_type}
        self.client.upload_file(str(source_path), self.bucket, key, **extra_args)
        return self._to_storage_uri(key)

    def read_text(self, storage_path: str) -> str:
        return self.read_bytes(storage_path).decode("utf-8", errors="ignore")

    def read_bytes(self, storage_path: str) -> bytes:
        bucket, key = self._parse_storage_uri(storage_path)
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    def copy_to_local_path(self, storage_path: str, target_path: Path) -> Path:
        bucket, key = self._parse_storage_uri(storage_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(bucket, key, str(target_path))
        return target_path

    def ensure_paths(self, paths: Iterable[Path]) -> None:
        return

    def delete(self, storage_path: str) -> None:
        bucket, key = self._parse_storage_uri(storage_path)
        self.client.delete_object(Bucket=bucket, Key=key)

    def build_preview_descriptor(self, artifact: object, settings: Settings) -> PreviewDescriptor:
        bucket, key = self._parse_storage_uri(str(getattr(artifact, "storage_path")))
        expires_in = settings.preview_url_ttl_seconds
        preview_url = self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ResponseContentDisposition": f'inline; filename="{getattr(artifact, "name", "artifact")}"',
                "ResponseContentType": getattr(artifact, "content_type", None) or "application/octet-stream",
            },
            ExpiresIn=expires_in,
        )
        return PreviewDescriptor(
            url=preview_url,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )

    def _build_key(self, *, session_id: str, folder: str, filename: str) -> str:
        segments = [segment for segment in (self.prefix, session_id, folder, filename) if segment]
        return "/".join(segments)

    def _to_storage_uri(self, key: str) -> str:
        return f"s3://{self.bucket}/{key}"

    @staticmethod
    def _parse_storage_uri(storage_path: str) -> tuple[str, str]:
        if not storage_path.startswith("s3://"):
            raise RuntimeError(f"Unsupported object storage locator: {storage_path}")
        bucket_and_key = storage_path[len("s3://") :]
        bucket, _, key = bucket_and_key.partition("/")
        if not bucket or not key:
            raise RuntimeError(f"Invalid object storage locator: {storage_path}")
        return bucket, key


class StorageService:
    """Facade around the configured storage backend."""

    def __init__(self, backend: StorageBackend | None = None) -> None:
        self.settings = get_settings()
        self.backend = backend or self._build_backend()

    def save_upload(self, session_id: str, upload: UploadFile, artifact_kind: str) -> tuple[str, int]:
        """Save an uploaded artifact."""
        return self.backend.save_upload(session_id=session_id, upload=upload, artifact_kind=artifact_kind)

    def save_bytes(self, session_id: str, folder: str, filename: str, content: bytes) -> str:
        """Save generated content."""
        return self.backend.save_bytes(session_id=session_id, folder=folder, filename=filename, content=content)

    def save_file(self, session_id: str, folder: str, filename: str, source_path: Path) -> str:
        """Save one generated local file."""
        return self.backend.save_file(session_id=session_id, folder=folder, filename=filename, source_path=source_path)

    def read_text(self, storage_path: str) -> str:
        """Read stored text content."""
        return self.backend.read_text(storage_path)

    def read_bytes(self, storage_path: str) -> bytes:
        """Read stored binary content."""
        return self.backend.read_bytes(storage_path)

    def copy_to_local_path(self, storage_path: str, target_path: Path) -> Path:
        """Materialize one stored object to a local file path."""
        return self.backend.copy_to_local_path(storage_path, target_path)

    def ensure_paths(self, paths: Iterable[Path]) -> None:
        """Ensure required local directories exist for the active backend."""
        self.backend.ensure_paths(paths)

    def delete(self, storage_path: str) -> None:
        """Delete one stored object if it exists."""
        self.backend.delete(storage_path)

    def build_preview_descriptor(self, artifact: object) -> PreviewDescriptor:
        """Return a preview descriptor for one artifact-like object."""
        return self.backend.build_preview_descriptor(artifact=artifact, settings=self.settings)

    def build_internal_artifact_path(self, storage_path: str) -> str | None:
        """Return an nginx-internal local artifact path when available."""
        if self.settings.storage_backend.lower() != "local":
            return None
        if not getattr(self.settings, "protected_artifact_internal_redirect_enabled", False):
            return None

        try:
            root = self.settings.local_storage_root.resolve()
            candidate = Path(storage_path).resolve()
            relative_path = candidate.relative_to(root)
        except Exception:
            return None

        return f"/_protected-artifacts/{relative_path.as_posix()}"

    def validate_preview_signature(self, artifact_id: str, expires: int, signature: str) -> None:
        """Validate one signed preview request."""
        if expires < int(datetime.now(UTC).timestamp()):
            raise RuntimeError("Preview URL has expired.")
        expected = _sign_preview_token(
            artifact_id=artifact_id,
            expires=expires,
            secret=self.settings.preview_url_signing_secret,
        )
        if not hmac.compare_digest(expected, signature):
            raise RuntimeError("Invalid preview signature.")

    def _build_backend(self) -> StorageBackend:
        from app.portability.storage_backend import select_storage_backend

        return select_storage_backend(self.settings)


def _guess_content_type(source_path: Path) -> str | None:
    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if suffix == ".png":
        return "image/png"
    if suffix == ".txt":
        return "text/plain"
    return None


def _sign_preview_token(*, artifact_id: str, expires: int, secret: str) -> str:
    payload = f"{artifact_id}:{expires}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
