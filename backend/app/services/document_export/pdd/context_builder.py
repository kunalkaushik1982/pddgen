r"""
PDD export: full walkthrough evidence (AS-IS steps, screenshots, diagrams, TO-BE hints).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate
from sqlalchemy.orm import Session

from app.models.draft_session import DraftSessionModel
from app.services.documents.document_context_builder_interfaces import DocumentContextBuilder
from app.services.document_export.common.workflow_context import SharedWorkflowExportContextBuilder
from app.services.document_export.enrichment.store import merge_enrichment_into_pdd_overview_summary
from app.services.document_export.pdd import process_summary_narrative
from app.storage.storage_service import StorageService


class PddDocumentExportContextBuilder(SharedWorkflowExportContextBuilder, DocumentContextBuilder):
    """Build the PDD-specific render context from shared workflow primitives."""

    document_type = "pdd"

    def _workflow_section_summary(
        self,
        process_name: str,
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
    ) -> str:
        return process_summary_narrative.build_pdd_section_summary(
            process_name=process_name,
            process_steps=process_steps,
            process_notes=process_notes,
        )

    def _workflow_process_summary(
        self,
        draft_session: DraftSessionModel,
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
    ) -> str:
        return process_summary_narrative.build_pdd_process_summary(draft_session, process_steps, process_notes)

    def build(
        self,
        db: Session,
        draft_session: DraftSessionModel,
        template_document: DocxTemplate,
        *,
        asset_root: Path,
        storage_service: StorageService,
    ) -> dict[str, Any]:
        shared_context = self.build_shared_context(
            db,
            draft_session,
            template_document,
            asset_root=asset_root,
            storage_service=storage_service,
        )
        process_summary = self._workflow_process_summary(
            draft_session,
            shared_context["process_steps"],
            shared_context["process_notes"],
        )
        process_summary = merge_enrichment_into_pdd_overview_summary(draft_session, process_summary)
        to_be_recommendations = self.process_diagram_service.build_to_be_suggestions(draft_session)
        process_sections = shared_context["process_sections"]
        multi_process = len(process_sections) > 1

        return {
            "session_title": draft_session.title,
            "owner_id": draft_session.owner_id,
            "process_steps": shared_context["process_steps"],
            "process_notes": shared_context["process_notes"],
            "process_sections": process_sections,
            "pdd": {
                "title": draft_session.title,
                "owner_id": draft_session.owner_id,
                "session_id": draft_session.id,
                "status": draft_session.status,
                "diagram_type": draft_session.diagram_type,
                "generated_at": shared_context["generated_at"],
                "multi_process": multi_process,
                "step_count": len(shared_context["process_steps"]),
                "note_count": len(shared_context["process_notes"]),
                "step_bullets": [step["bullet_entry"] for step in shared_context["process_steps"]],
                "overview": {
                    "process_name": draft_session.title,
                    "document_owner": draft_session.owner_id,
                    "document_status": draft_session.status,
                    "generated_at": shared_context["generated_at"],
                    "process_summary": process_summary,
                },
                "process_sections": process_sections,
                "as_is_steps": shared_context["process_steps"],
                "to_be_recommendations": to_be_recommendations,
                "process_flow": {
                    "mermaid_source": shared_context["diagram_source"],
                    "diagram_source": shared_context["diagram_source"],
                    "diagram_path": shared_context["rendered_diagram_path"],
                    "diagram_image": self._build_process_diagram_image(template_document, shared_context["rendered_diagram_path"]),
                    "detailed_path": shared_context["rendered_diagram_path"],
                    "detailed_image": self._build_process_diagram_image(template_document, shared_context["rendered_diagram_path"]),
                    "rendered": bool(shared_context["rendered_diagram_path"]),
                },
                "business_rules": shared_context["process_notes"],
            },
        }


class DocumentExportContextBuilder(PddDocumentExportContextBuilder):
    """Backward-compatible alias for the default PDD export builder."""

    pass
