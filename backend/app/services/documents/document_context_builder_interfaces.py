r"""
Purpose: Typed contracts for document-specific export context builders.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_context_builder_interfaces.py
"""

from __future__ import annotations

from typing import Any, Protocol
from pathlib import Path

from docxtpl import DocxTemplate
from sqlalchemy.orm import Session

from app.models.draft_session import DraftSessionModel
from app.storage.storage_service import StorageService


class DocumentContextBuilder(Protocol):
    """Build a template render context for one document type."""

    document_type: str

    def build(
        self,
        db: Session,
        draft_session: DraftSessionModel,
        template_document: DocxTemplate,
        *,
        asset_root: Path,
        storage_service: StorageService,
    ) -> dict[str, Any]:
        """Return the template context for the target document type."""
        ...
