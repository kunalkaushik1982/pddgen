r"""
Purpose: Render DOCX templates to output files for document exports.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_template_renderer.py
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from docxtpl import DocxTemplate
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.draft_session import DraftSessionModel
from app.services.document_export_context_builder import DocumentExportContextBuilder
from app.storage.storage_service import StorageService


class DocumentTemplateRenderer:
    """Render DOCX output files from a draft session and a template artifact."""

    def __init__(self, context_builder: DocumentExportContextBuilder | None = None) -> None:
        self.context_builder = context_builder or DocumentExportContextBuilder()

    def render_docx_file(
        self,
        db: Session,
        draft_session: DraftSessionModel,
        output_path: Path,
        storage_service: StorageService,
    ) -> None:
        template_artifact = self._get_template_artifact(draft_session)
        with TemporaryDirectory(prefix=f"pdd_export_assets_{draft_session.id}_") as asset_dir:
            asset_root = Path(asset_dir)
            template_path = storage_service.copy_to_local_path(
                template_artifact.storage_path,
                asset_root / "template" / template_artifact.name,
            )
            doc = DocxTemplate(str(template_path))
            doc.render(self.context_builder.build(db, draft_session, doc, asset_root=asset_root, storage_service=storage_service))
            doc.save(str(output_path))

    @staticmethod
    def _get_template_artifact(draft_session: DraftSessionModel):
        template_artifact = next((artifact for artifact in draft_session.artifacts if artifact.kind == "template"), None)
        if template_artifact is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A template artifact is required before export.",
            )
        return template_artifact
