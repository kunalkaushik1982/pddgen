r"""
Purpose: Render DOCX templates to output files for document exports.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_template_renderer.py
"""

from __future__ import annotations

from pathlib import Path

from docxtpl import DocxTemplate
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.draft_session import DraftSessionModel
from app.services.document_export_context_builder import DocumentExportContextBuilder


class DocumentTemplateRenderer:
    """Render DOCX output files from a draft session and a template artifact."""

    def __init__(self, context_builder: DocumentExportContextBuilder | None = None) -> None:
        self.settings = get_settings()
        self.context_builder = context_builder or DocumentExportContextBuilder()

    def build_output_path(self, draft_session: DraftSessionModel, extension: str) -> Path:
        output_name = f"{draft_session.id}_draft.{extension}"
        output_path = self.settings.local_storage_root / draft_session.id / self.settings.docx_output_folder / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    def render_docx_file(self, db: Session, draft_session: DraftSessionModel, output_path: Path) -> None:
        template_path = self._get_template_path(draft_session)
        doc = DocxTemplate(str(template_path))
        doc.render(self.context_builder.build(db, draft_session, doc))
        doc.save(str(output_path))

    @staticmethod
    def _get_template_path(draft_session: DraftSessionModel) -> Path:
        template_artifact = next((artifact for artifact in draft_session.artifacts if artifact.kind == "template"), None)
        if template_artifact is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A template artifact is required before export.",
            )

        template_path = Path(template_artifact.storage_path)
        if not template_path.exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template file was not found on storage.")
        return template_path
