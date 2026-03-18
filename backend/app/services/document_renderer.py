r"""
Purpose: Service facade for deterministic document export rendering.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_renderer.py
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy.orm import Session

from app.models.draft_session import DraftSessionModel
from app.models.output_document import OutputDocumentModel
from app.services.document_pdf_converter import DocumentPdfConverter
from app.services.document_template_renderer import DocumentTemplateRenderer
from app.storage.storage_service import StorageService


class DocumentRendererService:
    """Facade that coordinates template rendering and file conversion for exports."""

    def __init__(
        self,
        storage_service: StorageService | None = None,
        template_renderer: DocumentTemplateRenderer | None = None,
        pdf_converter: DocumentPdfConverter | None = None,
    ) -> None:
        self.storage_service = storage_service or StorageService()
        self.template_renderer = template_renderer or DocumentTemplateRenderer()
        self.pdf_converter = pdf_converter or DocumentPdfConverter()

    def render_docx(self, db: Session, draft_session: DraftSessionModel) -> OutputDocumentModel:
        output_path = self.template_renderer.build_output_path(draft_session, "docx")
        self.template_renderer.render_docx_file(db, draft_session, output_path)
        return self._persist_output_document(db, draft_session, kind="docx", output_path=output_path)

    def render_pdf(self, db: Session, draft_session: DraftSessionModel) -> OutputDocumentModel:
        output_path = self.template_renderer.build_output_path(draft_session, "pdf")
        with TemporaryDirectory(prefix=f"pdd_{draft_session.id}_") as temp_dir:
            temp_docx_path = Path(temp_dir) / f"{draft_session.id}_draft.docx"
            self.template_renderer.render_docx_file(db, draft_session, temp_docx_path)
            self.pdf_converter.convert(temp_docx_path, output_path)
        return self._persist_output_document(db, draft_session, kind="pdf", output_path=output_path)

    @staticmethod
    def _persist_output_document(
        db: Session,
        draft_session: DraftSessionModel,
        kind: str,
        output_path: Path,
    ) -> OutputDocumentModel:
        output_document = OutputDocumentModel(
            session_id=draft_session.id,
            kind=kind,
            storage_path=str(output_path),
        )
        db.add(output_document)
        draft_session.status = "exported"
        db.commit()
        db.refresh(output_document)
        return output_document
