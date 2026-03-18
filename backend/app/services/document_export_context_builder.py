r"""
Purpose: Build DOCX export context data from a reviewed draft session.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_export_context_builder.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.artifact import ArtifactModel
from app.models.diagram_layout import DiagramLayoutModel
from app.models.draft_session import DraftSessionModel
from app.services.process_diagram_service import ProcessDiagramService


class DocumentExportContextBuilder:
    """Build the render context for document exports."""

    def __init__(
        self,
        process_diagram_service: ProcessDiagramService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.process_diagram_service = process_diagram_service or ProcessDiagramService()

    def build(self, db: Session, draft_session: DraftSessionModel, template_document: DocxTemplate) -> dict[str, Any]:
        screenshot_map = {
            artifact.id: artifact
            for artifact in draft_session.artifacts
            if artifact.kind == "screenshot"
        }
        diagram_source = self.process_diagram_service.build_diagram_source(draft_session)
        output_dir = self.settings.local_storage_root / draft_session.id / self.settings.docx_output_folder
        output_dir.mkdir(parents=True, exist_ok=True)
        detailed_saved_positions = self._load_saved_diagram_positions(db, draft_session.id, "detailed")

        detailed_diagram_path = None
        if (draft_session.diagram_type or "flowchart").lower() == "flowchart":
            stored_diagram_path = self._resolve_saved_diagram_artifact_path(db, draft_session.id)
            if stored_diagram_path:
                detailed_diagram_path = stored_diagram_path
            else:
                detailed_diagram_path = self.process_diagram_service.render_flowchart_view(
                    draft_session,
                    "detailed",
                    output_dir / f"{draft_session.id}_detailed.png",
                    saved_positions=detailed_saved_positions,
                )
        else:
            detailed_diagram_path = self.process_diagram_service.render_sequence_diagram(
                draft_session,
                output_dir / f"{draft_session.id}_sequence.png",
            )

        process_steps = [
            self._build_step_context(step, screenshot_map, template_document)
            for step in sorted(draft_session.process_steps, key=lambda item: item.step_number)
        ]
        process_notes = [
            {
                "text": note.text,
                "confidence": note.confidence,
                "inference_type": note.inference_type,
            }
            for note in draft_session.process_notes
        ]
        to_be_recommendations = self.process_diagram_service.build_to_be_suggestions(draft_session)
        process_summary = self._build_process_summary(draft_session, process_steps, process_notes)
        generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        rendered_diagram_path = str(detailed_diagram_path) if detailed_diagram_path else ""

        return {
            "session_title": draft_session.title,
            "owner_id": draft_session.owner_id,
            "process_steps": process_steps,
            "process_notes": process_notes,
            "pdd": {
                "title": draft_session.title,
                "owner_id": draft_session.owner_id,
                "session_id": draft_session.id,
                "status": draft_session.status,
                "diagram_type": draft_session.diagram_type,
                "generated_at": generated_at,
                "step_count": len(process_steps),
                "note_count": len(process_notes),
                "step_bullets": [step["bullet_entry"] for step in process_steps],
                "overview": {
                    "process_name": draft_session.title,
                    "document_owner": draft_session.owner_id,
                    "document_status": draft_session.status,
                    "generated_at": generated_at,
                    "process_summary": process_summary,
                },
                "as_is_steps": process_steps,
                "to_be_recommendations": to_be_recommendations,
                "process_flow": {
                    "mermaid_source": diagram_source,
                    "diagram_source": diagram_source,
                    "diagram_path": rendered_diagram_path,
                    "diagram_image": self._build_process_diagram_image(template_document, rendered_diagram_path),
                    "detailed_path": rendered_diagram_path,
                    "detailed_image": self._build_process_diagram_image(template_document, rendered_diagram_path),
                    "rendered": bool(detailed_diagram_path),
                },
                "business_rules": process_notes,
            },
        }

    @staticmethod
    def _build_process_summary(
        draft_session: DraftSessionModel,
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
    ) -> str:
        applications = [
            item
            for item in dict.fromkeys(
                str(step.get("application_name", "") or "").strip()
                for step in process_steps
            )
            if item
        ]
        action_samples = [
            str(step.get("action_text", "") or "").strip().rstrip(".")
            for step in process_steps[:4]
            if str(step.get("action_text", "") or "").strip()
        ]
        note_samples = [
            str(note.get("text", "") or "").strip().rstrip(".")
            for note in process_notes[:2]
            if str(note.get("text", "") or "").strip()
        ]

        process_name = (draft_session.title or "the observed business process").strip()
        application_text = ", ".join(applications) if applications else "the supporting business application landscape"
        step_count = len(process_steps)

        summary_parts = [
            (
                f"The AS-IS process documented in this draft captures how {process_name} is currently executed within "
                f"{application_text}. The walkthrough reflects the observed user activity required to complete the business objective, "
                f"with the process broken into {step_count} ordered step{'s' if step_count != 1 else ''} for review and refinement."
            )
        ]

        if action_samples:
            if len(action_samples) == 1:
                action_text = action_samples[0]
            else:
                action_text = ", ".join(action_samples[:-1]) + f", and {action_samples[-1]}"
            summary_parts.append(
                f"Across the captured flow, the user moves through actions such as {action_text}, showing how the transaction progresses from initiation through validation and completion."
            )

        if applications:
            summary_parts.append(
                f"The applications involved in this process include {application_text}, which together support the operational controls, data entry points, and review checkpoints required to complete the work accurately."
            )

        if note_samples:
            note_text = note_samples[0] if len(note_samples) == 1 else " and ".join(note_samples)
            summary_parts.append(
                f"During the walkthrough, additional business context was also identified, including {note_text}, which helps explain the intent, dependencies, and control expectations behind the recorded steps."
            )

        summary_parts.append(
            "This section should be used as a narrative summary of the current-state process before reviewing the detailed step bullets, primary screenshots, and supporting process flow diagram."
        )
        return " ".join(summary_parts)

    @staticmethod
    def _load_saved_diagram_positions(
        db: Session,
        session_id: str,
        view_type: str,
    ) -> dict[str, dict[str, float | str]]:
        layout = (
            db.query(DiagramLayoutModel)
            .filter(DiagramLayoutModel.session_id == session_id, DiagramLayoutModel.view_type == view_type)
            .one_or_none()
        )
        if layout is None or not layout.layout_json:
            return {}
        try:
            parsed = json.loads(layout.layout_json)
        except json.JSONDecodeError:
            return {}
        items = parsed.get("nodes", []) if isinstance(parsed, dict) else parsed

        saved_positions: dict[str, dict[str, float | str]] = {}
        for item in items:
            node_id = item.get("id")
            if not node_id:
                continue
            saved_positions[node_id] = {
                "x": float(item.get("x", 0)),
                "y": float(item.get("y", 0)),
                "label": str(item.get("label", "")) if item.get("label") else "",
            }
        return saved_positions

    @staticmethod
    def _resolve_saved_diagram_artifact_path(db: Session, session_id: str) -> str:
        artifact = (
            db.query(ArtifactModel)
            .filter(
                ArtifactModel.session_id == session_id,
                ArtifactModel.kind == "diagram",
                ArtifactModel.name == "detailed-process-flow.png",
            )
            .order_by(ArtifactModel.created_at.desc())
            .first()
        )
        if artifact is None:
            return ""
        diagram_path = Path(artifact.storage_path)
        return str(diagram_path) if diagram_path.exists() else ""

    def _build_step_context(
        self,
        step: Any,
        screenshot_map: dict[str, ArtifactModel],
        template_document: DocxTemplate,
    ) -> dict[str, Any]:
        screenshot_items = []
        primary_screenshot_path = ""
        for step_screenshot in sorted(step.step_screenshots, key=lambda item: item.sequence_number):
            screenshot_path = self._resolve_screenshot_path(step_screenshot.artifact_id, screenshot_map)
            if step_screenshot.is_primary and screenshot_path:
                primary_screenshot_path = screenshot_path
            screenshot_items.append(
                {
                    "role": step_screenshot.role.title(),
                    "timestamp": step_screenshot.timestamp,
                    "selection_method": step_screenshot.selection_method,
                    "path": screenshot_path,
                    "image": self._build_inline_image(template_document, screenshot_path),
                    "is_primary": step_screenshot.is_primary,
                }
            )

        if not primary_screenshot_path:
            primary_screenshot_path = self._resolve_screenshot_path(step.screenshot_id, screenshot_map)
        primary_screenshot_image = self._build_inline_image(template_document, primary_screenshot_path)

        return {
            "step_number": step.step_number,
            "application_name": step.application_name,
            "action_text": step.action_text,
            "source_data_note": step.source_data_note,
            "timestamp": step.timestamp,
            "start_timestamp": step.start_timestamp,
            "end_timestamp": step.end_timestamp,
            "supporting_transcript_text": step.supporting_transcript_text,
            "confidence": step.confidence,
            "evidence_references": json.loads(step.evidence_references or "[]"),
            "bullet_entry": f"Step {step.step_number}. {step.action_text}",
            "primary_screenshot_path": primary_screenshot_path,
            "primary_screenshot_image": primary_screenshot_image,
            "has_primary_screenshot": bool(primary_screenshot_path),
            "screenshot_path": primary_screenshot_path,
            "screenshot_image": primary_screenshot_image,
            "screenshots": screenshot_items,
        }

    @staticmethod
    def _resolve_screenshot_path(screenshot_id: str, screenshot_map: dict[str, ArtifactModel]) -> str:
        if not screenshot_id:
            return ""
        artifact = screenshot_map.get(screenshot_id)
        if artifact is None:
            return ""
        path = Path(artifact.storage_path)
        return str(path) if path.exists() else ""

    @staticmethod
    def _build_inline_image(template_document: DocxTemplate, screenshot_path: str) -> InlineImage | str:
        if not screenshot_path:
            return ""
        try:
            return InlineImage(template_document, screenshot_path, width=Mm(140))
        except Exception:
            return ""

    @staticmethod
    def _build_process_diagram_image(template_document: DocxTemplate, diagram_path: str) -> InlineImage | str:
        if not diagram_path:
            return ""
        try:
            with Image.open(diagram_path) as image:
                width_px, height_px = image.size
        except Exception:
            return ""

        max_width_mm = 170.0
        max_height_mm = 220.0
        if width_px <= 0 or height_px <= 0:
            return ""

        aspect_ratio = height_px / width_px
        target_width_mm = max_width_mm
        target_height_mm = target_width_mm * aspect_ratio
        if target_height_mm > max_height_mm:
            target_height_mm = max_height_mm
            target_width_mm = target_height_mm / aspect_ratio

        try:
            return InlineImage(
                template_document,
                diagram_path,
                width=Mm(target_width_mm),
                height=Mm(target_height_mm),
            )
        except Exception:
            return ""
