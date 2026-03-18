r"""
Purpose: Validation rules for uploaded artifacts before persistence.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\artifact_validation.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class ArtifactValidationRule:
    """Validation policy for one artifact kind."""

    allowed_extensions: frozenset[str]
    allowed_content_types: frozenset[str]
    max_size_mb: int | None = None


class ArtifactValidationService:
    """Validate uploaded files against artifact-kind-specific policies."""

    _RULES: dict[str, ArtifactValidationRule] = {
        "video": ArtifactValidationRule(
            allowed_extensions=frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}),
            allowed_content_types=frozenset(
                {
                    "video/mp4",
                    "video/quicktime",
                    "video/x-msvideo",
                    "video/x-matroska",
                    "video/webm",
                    "video/x-m4v",
                    "application/octet-stream",
                }
            ),
        ),
        "transcript": ArtifactValidationRule(
            allowed_extensions=frozenset({".txt", ".vtt", ".docx"}),
            allowed_content_types=frozenset(
                {
                    "text/plain",
                    "text/vtt",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/octet-stream",
                }
            ),
            max_size_mb=25,
        ),
        "template": ArtifactValidationRule(
            allowed_extensions=frozenset({".docx"}),
            allowed_content_types=frozenset(
                {
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/octet-stream",
                }
            ),
            max_size_mb=25,
        ),
        "sop": ArtifactValidationRule(
            allowed_extensions=frozenset({".pdf", ".docx", ".txt"}),
            allowed_content_types=frozenset(
                {
                    "application/pdf",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "text/plain",
                    "application/octet-stream",
                }
            ),
            max_size_mb=50,
        ),
        "diagram": ArtifactValidationRule(
            allowed_extensions=frozenset({".png", ".jpg", ".jpeg", ".svg"}),
            allowed_content_types=frozenset(
                {
                    "image/png",
                    "image/jpeg",
                    "image/svg+xml",
                    "application/octet-stream",
                }
            ),
            max_size_mb=20,
        ),
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def validate_upload(self, *, upload: UploadFile, artifact_kind: str) -> int:
        """Validate one upload and return its file size in bytes."""
        rule = self._RULES.get(artifact_kind)
        if rule is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported artifact kind '{artifact_kind}'.")

        filename = (upload.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must include a filename.")

        extension = Path(filename).suffix.lower()
        if extension not in rule.allowed_extensions:
            allowed = ", ".join(sorted(rule.allowed_extensions))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{artifact_kind.title()} files must use one of: {allowed}.",
            )

        content_type = (upload.content_type or "").strip().lower()
        if content_type and content_type not in rule.allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{artifact_kind.title()} upload content type '{content_type}' is not allowed.",
            )

        size_bytes = self._get_upload_size(upload)
        max_size_bytes = (rule.max_size_mb or self.settings.max_upload_size_mb) * 1024 * 1024
        if size_bytes <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
        if size_bytes > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{artifact_kind.title()} upload exceeds the maximum allowed size.",
            )
        return size_bytes

    @staticmethod
    def _get_upload_size(upload: UploadFile) -> int:
        current_position = upload.file.tell()
        upload.file.seek(0, 2)
        size_bytes = upload.file.tell()
        upload.file.seek(current_position)
        return size_bytes
