r"""
Purpose: Render DOCX templates to output files for document exports.
Document-type-specific preprocessing (e.g. PDD multi-process XML) lives under ``document_export/<type>/``.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_template_renderer.py
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from docxtpl import DocxTemplate
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.draft_session import DraftSessionModel
from app.services.documents.document_context_builder_interfaces import DocumentContextBuilder
from app.services.documents.document_context_builder_registry import DocumentContextBuilderRegistry
from app.services.documents.document_context_builder_registration import register_workflow_document_builders
from app.services.document_export.brd.template_preparation import prepare_brd_template_if_needed
from app.services.document_export.pdd.template_preparation import prepare_pdd_multi_process_template
from app.services.document_export.sop.template_preparation import prepare_sop_template_if_needed
from app.services.generation.process_diagram_service import ProcessDiagramService
from app.storage.storage_service import StorageService


class DocumentTemplateRenderer:
    """Render DOCX output files from a draft session and a template artifact."""

    def __init__(
        self,
        *,
        process_diagram_service: ProcessDiagramService,
        context_builder: DocumentContextBuilder | None = None,
    ) -> None:
        self.context_builder = context_builder
        self._process_diagram_service = process_diagram_service
        self.builder_registry = self._build_default_registry()

    def render_docx_file(
        self,
        db: Session,
        draft_session: DraftSessionModel,
        output_path: Path,
        storage_service: StorageService,
    ) -> None:
        template_artifact = self._get_template_artifact(draft_session)
        with TemporaryDirectory(prefix=f"docx_export_assets_{draft_session.id}_") as asset_dir:
            asset_root = Path(asset_dir)
            template_path = storage_service.copy_to_local_path(
                template_artifact.storage_path,
                asset_root / "template" / template_artifact.name,
            )
            prepare_pdd_multi_process_template(template_path, draft_session)
            prepare_brd_template_if_needed(template_path, draft_session)
            prepare_sop_template_if_needed(template_path, draft_session)
            doc = DocxTemplate(str(template_path))
            context_builder = self.context_builder or self.builder_registry.create(getattr(draft_session, "document_type", "pdd"))
            doc.render(context_builder.build(db, draft_session, doc, asset_root=asset_root, storage_service=storage_service))
            doc.save(str(output_path))

    def _build_default_registry(self) -> DocumentContextBuilderRegistry:
        registry = DocumentContextBuilderRegistry()
        register_workflow_document_builders(registry, process_diagram_service=self._process_diagram_service)
        return registry

    @staticmethod
    def _get_template_artifact(draft_session: DraftSessionModel):
        template_artifact = next((artifact for artifact in draft_session.artifacts if artifact.kind == "template"), None)
        if template_artifact is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A template artifact is required before export.",
            )
        return template_artifact
