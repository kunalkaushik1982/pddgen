r"""
Purpose: Build DOCX export context data from a reviewed draft session.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_export_context_builder.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.artifact import ArtifactModel
from app.models.diagram_layout import DiagramLayoutModel
from app.models.draft_session import DraftSessionModel
from app.services.document_context_builder_interfaces import DocumentContextBuilder
from app.services.process_diagram_service import ProcessDiagramService
from app.storage.storage_service import StorageService


class SharedWorkflowExportContextBuilder:
    """Build shared workflow/export primitives independent of a final document type."""

    def __init__(
        self,
        process_diagram_service: ProcessDiagramService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.process_diagram_service = process_diagram_service or ProcessDiagramService()

    def build_shared_context(
        self,
        db: Session,
        draft_session: DraftSessionModel,
        template_document: DocxTemplate,
        *,
        asset_root: Path,
        storage_service: StorageService,
    ) -> dict[str, Any]:
        screenshot_map = {
            artifact.id: artifact
            for artifact in draft_session.artifacts
            if artifact.kind == "screenshot"
        }
        output_dir = asset_root / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)

        process_steps = [
            self._build_step_context(
                step,
                screenshot_map,
                template_document,
                storage_service=storage_service,
                asset_root=asset_root,
            )
            for step in sorted(draft_session.process_steps, key=lambda item: item.step_number)
        ]
        process_notes = [
            {
                "process_group_id": note.process_group_id,
                "text": note.text,
                "confidence": note.confidence,
                "inference_type": note.inference_type,
            }
            for note in draft_session.process_notes
        ]
        process_sections = self._build_process_sections(
            db,
            draft_session,
            template_document,
            output_dir=output_dir,
            process_steps=process_steps,
            process_notes=process_notes,
        )
        to_be_recommendations = self.process_diagram_service.build_to_be_suggestions(draft_session)
        process_summary = self._build_process_summary(draft_session, process_steps, process_notes)
        generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        rendered_diagram_path = (
            process_sections[0]["diagram_path"]
            if len(process_sections) == 1
            else self._build_combined_process_diagram_image(
                output_dir=output_dir,
                session_id=draft_session.id,
                process_sections=process_sections,
            )
        )
        diagram_source = "\n\n".join(section["diagram_source"] for section in process_sections if section["diagram_source"])

        return {
            "session_title": draft_session.title,
            "owner_id": draft_session.owner_id,
            "document_type": getattr(draft_session, "document_type", "pdd"),
            "generated_at": generated_at,
            "process_steps": process_steps,
            "process_notes": process_notes,
            "process_sections": process_sections,
            "process_summary": process_summary,
            "to_be_recommendations": to_be_recommendations,
            "diagram_source": diagram_source,
            "rendered_diagram_path": rendered_diagram_path,
        }

    def _build_process_sections(
        self,
        db: Session,
        draft_session: DraftSessionModel,
        template_document: DocxTemplate,
        *,
        output_dir: Path,
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        process_groups = sorted(getattr(draft_session, "process_groups", []), key=lambda item: item.display_order)
        if not process_groups:
            process_groups = [None]

        sections: list[dict[str, Any]] = []
        for index, process_group in enumerate(process_groups, start=1):
            process_group_id = getattr(process_group, "id", None)
            group_title = getattr(process_group, "title", "") or draft_session.title
            group_steps = [step for step in process_steps if process_group is None or step.get("process_group_id") == process_group_id]
            group_notes = [note for note in process_notes if process_group is None or note.get("process_group_id") == process_group_id]
            if process_group is not None and not group_steps and not group_notes:
                continue
            scoped_session = (
                draft_session
                if process_group is None
                else self.process_diagram_service._scope_session(draft_session, process_group_id)
            )
            diagram_source = self.process_diagram_service.build_diagram_source(scoped_session)
            detailed_diagram_path = self._render_process_diagram(
                db,
                draft_session,
                output_dir=output_dir,
                process_group_id=process_group_id,
                section_index=index,
            )
            rendered_diagram_path = str(detailed_diagram_path) if detailed_diagram_path else ""
            sections.append(
                {
                    "process_group_id": process_group_id,
                    "title": group_title,
                    "summary": self._build_single_process_summary(
                        process_name=group_title,
                        process_steps=group_steps,
                        process_notes=group_notes,
                    ),
                    "steps": group_steps,
                    "notes": group_notes,
                    "step_bullets": [step["bullet_entry"] for step in group_steps],
                    "diagram_source": diagram_source,
                    "diagram_path": rendered_diagram_path,
                    "diagram_image": self._build_process_diagram_image(template_document, rendered_diagram_path),
                    "diagram_rendered": bool(detailed_diagram_path),
                }
            )
        return sections

    def _render_process_diagram(
        self,
        db: Session,
        draft_session: DraftSessionModel,
        *,
        output_dir: Path,
        process_group_id: str | None,
        section_index: int,
    ) -> str:
        if (draft_session.diagram_type or "flowchart").lower() != "flowchart":
            path = self.process_diagram_service.render_sequence_diagram(
                (
                    draft_session
                    if process_group_id is None
                    else self.process_diagram_service._scope_session(draft_session, process_group_id)
                ),
                output_dir / f"{draft_session.id}_sequence_{section_index}.png",
            )
            return str(path) if path else ""

        saved_positions = self._load_saved_diagram_positions(
            db,
            draft_session.id,
            "detailed",
            process_group_id=process_group_id,
        )
        path = self.process_diagram_service.render_flowchart_view(
            draft_session,
            "detailed",
            output_dir / f"{draft_session.id}_detailed_{section_index}.png",
            saved_positions=saved_positions,
            process_group_id=process_group_id,
        )
        return str(path) if path else ""

    @staticmethod
    def _build_combined_process_diagram_image(
        *,
        output_dir: Path,
        session_id: str,
        process_sections: list[dict[str, Any]],
    ) -> str:
        diagram_paths = [section["diagram_path"] for section in process_sections if section.get("diagram_path")]
        if not diagram_paths:
            return ""
        if len(diagram_paths) == 1:
            return str(diagram_paths[0])

        images: list[Image.Image] = []
        try:
            for path in diagram_paths:
                images.append(Image.open(path).convert("RGB"))
            max_width = max(image.width for image in images)
            spacing = 48
            title_band = 64
            total_height = sum(image.height for image in images) + spacing * (len(images) - 1) + title_band * len(images)
            combined = Image.new("RGB", (max_width, total_height), "white")
            draw = ImageDraw.Draw(combined)
            font = ImageFont.load_default()
            current_y = 0
            for image, section in zip(images, process_sections, strict=False):
                title = str(section.get("title", "") or "")
                if title:
                    draw.text((24, current_y + 20), title, fill="#000000", font=font)
                current_y += title_band
                combined.paste(image, ((max_width - image.width) // 2, current_y))
                current_y += image.height + spacing
            output_path = output_dir / f"{session_id}_combined_process_diagram.png"
            combined.save(output_path, format="PNG", optimize=True)
            return str(output_path)
        finally:
            for image in images:
                image.close()

    @staticmethod
    def _build_process_summary(
        draft_session: DraftSessionModel,
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
    ) -> str:
        process_groups = sorted(getattr(draft_session, "process_groups", []), key=lambda item: item.display_order)
        if len(process_groups) > 1:
            grouped_sections: list[str] = []
            for process_group in process_groups:
                group_steps = [step for step in process_steps if step.get("process_group_id") == process_group.id]
                group_notes = [note for note in process_notes if note.get("process_group_id") == process_group.id]
                if not group_steps and not group_notes:
                    continue
                grouped_sections.append(
                    SharedWorkflowExportContextBuilder._build_single_process_summary(
                        process_name=process_group.title or draft_session.title,
                        process_steps=group_steps,
                        process_notes=group_notes,
                    )
                )
            if grouped_sections:
                return " ".join(grouped_sections)

        return SharedWorkflowExportContextBuilder._build_single_process_summary(
            process_name=draft_session.title,
            process_steps=process_steps,
            process_notes=process_notes,
        )

    @staticmethod
    def _build_single_process_summary(
        *,
        process_name: str,
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

        process_name = (process_name or "the observed business process").strip()
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
        *,
        process_group_id: str | None = None,
    ) -> dict[str, dict[str, float | str]]:
        layout = (
            db.query(DiagramLayoutModel)
            .filter(
                DiagramLayoutModel.session_id == session_id,
                DiagramLayoutModel.view_type == view_type,
                DiagramLayoutModel.process_group_id == process_group_id,
            )
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

    def _resolve_saved_diagram_artifact_path(
        self,
        db: Session,
        session_id: str,
        *,
        storage_service: StorageService,
        asset_root: Path,
    ) -> str:
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
        diagram_path = storage_service.copy_to_local_path(
            artifact.storage_path,
            asset_root / "diagram" / artifact.name,
        )
        return str(diagram_path)

    def _build_step_context(
        self,
        step: Any,
        screenshot_map: dict[str, ArtifactModel],
        template_document: DocxTemplate,
        *,
        storage_service: StorageService,
        asset_root: Path,
    ) -> dict[str, Any]:
        screenshot_items = []
        primary_screenshot_path = ""
        for step_screenshot in sorted(step.step_screenshots, key=lambda item: item.sequence_number):
            screenshot_path = self._resolve_screenshot_path(
                step_screenshot.artifact_id,
                screenshot_map,
                storage_service=storage_service,
                asset_root=asset_root,
            )
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
            primary_screenshot_path = self._resolve_screenshot_path(
                step.screenshot_id,
                screenshot_map,
                storage_service=storage_service,
                asset_root=asset_root,
            )
        primary_screenshot_image = self._build_inline_image(template_document, primary_screenshot_path)

        return {
            "process_group_id": step.process_group_id,
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
    def _resolve_screenshot_path(
        screenshot_id: str,
        screenshot_map: dict[str, ArtifactModel],
        *,
        storage_service: StorageService,
        asset_root: Path,
    ) -> str:
        if not screenshot_id:
            return ""
        artifact = screenshot_map.get(screenshot_id)
        if artifact is None:
            return ""
        path = storage_service.copy_to_local_path(
            artifact.storage_path,
            asset_root / "screenshots" / artifact.name,
        )
        return str(path)

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


class PddDocumentExportContextBuilder(SharedWorkflowExportContextBuilder, DocumentContextBuilder):
    """Build the PDD-specific render context from shared workflow primitives."""

    document_type = "pdd"

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

        return {
            "session_title": draft_session.title,
            "owner_id": draft_session.owner_id,
            "process_steps": shared_context["process_steps"],
            "process_notes": shared_context["process_notes"],
            "process_sections": shared_context["process_sections"],
            "pdd": {
                "title": draft_session.title,
                "owner_id": draft_session.owner_id,
                "session_id": draft_session.id,
                "status": draft_session.status,
                "diagram_type": draft_session.diagram_type,
                "generated_at": shared_context["generated_at"],
                "step_count": len(shared_context["process_steps"]),
                "note_count": len(shared_context["process_notes"]),
                "step_bullets": [step["bullet_entry"] for step in shared_context["process_steps"]],
                "overview": {
                    "process_name": draft_session.title,
                    "document_owner": draft_session.owner_id,
                    "document_status": draft_session.status,
                    "generated_at": shared_context["generated_at"],
                    "process_summary": shared_context["process_summary"],
                },
                "process_sections": shared_context["process_sections"],
                "as_is_steps": shared_context["process_steps"],
                "to_be_recommendations": shared_context["to_be_recommendations"],
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


class SopDocumentExportContextBuilder(SharedWorkflowExportContextBuilder, DocumentContextBuilder):
    """Build the SOP-specific render context from shared workflow primitives."""

    document_type = "sop"

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
        process_steps = shared_context["process_steps"]
        process_notes = shared_context["process_notes"]
        process_sections = shared_context["process_sections"]
        applications = self._collect_unique_values(process_steps, "application_name")
        responsibilities = self._build_sop_responsibilities(draft_session, applications)
        prerequisites = self._build_sop_prerequisites(applications, process_notes)
        controls = self._build_sop_controls(process_notes)
        expected_outcomes = self._build_sop_expected_outcomes(process_sections, process_notes)
        procedure_sections = [
            self._build_sop_procedure_section(section)
            for section in process_sections
        ]
        evidence_summary = self._build_sop_evidence_summary(
            process_steps=process_steps,
            process_notes=process_notes,
            process_sections=process_sections,
        )

        return {
            "session_title": draft_session.title,
            "owner_id": draft_session.owner_id,
            "process_steps": process_steps,
            "process_notes": process_notes,
            "process_sections": process_sections,
            "sop": {
                "title": draft_session.title,
                "owner_id": draft_session.owner_id,
                "session_id": draft_session.id,
                "status": draft_session.status,
                "diagram_type": draft_session.diagram_type,
                "generated_at": shared_context["generated_at"],
                "purpose": (
                    f"This SOP defines the observed operating procedure for {draft_session.title} "
                    "using the reviewed walkthrough evidence as the source of truth."
                ),
                "scope": self._build_sop_scope(draft_session.title, process_sections, process_steps),
                "applications": applications,
                "prerequisites": prerequisites,
                "responsibilities": responsibilities,
                "controls": controls,
                "expected_outcomes": expected_outcomes,
                "procedure_sections": procedure_sections,
                "supporting_notes": process_notes,
                "evidence_summary": evidence_summary,
                "procedure_step_count": len(process_steps),
                "procedure_section_count": len(procedure_sections),
                "supporting_note_count": len(process_notes),
            },
        }

    @staticmethod
    def _collect_unique_values(process_steps: list[dict[str, Any]], key: str) -> list[str]:
        return [
            item
            for item in dict.fromkeys(
                str(step.get(key, "") or "").strip()
                for step in process_steps
            )
            if item
        ]

    @staticmethod
    def _build_sop_scope(
        process_name: str,
        process_sections: list[dict[str, Any]],
        process_steps: list[dict[str, Any]],
    ) -> str:
        if process_sections:
            section_names = ", ".join(section["title"] for section in process_sections[:3] if section.get("title"))
            if len(process_sections) > 3:
                section_names += ", and related supporting sections"
            return (
                f"This SOP applies to the current-state execution of {process_name} across "
                f"{len(process_sections)} workflow section(s) and {len(process_steps)} documented step(s), "
                f"including areas such as {section_names}."
            )
        return (
            f"This SOP applies to the current-state execution of {process_name} and covers "
            f"{len(process_steps)} documented step(s) captured from the reviewed evidence."
        )

    @staticmethod
    def _build_sop_responsibilities(
        draft_session: DraftSessionModel,
        applications: list[str],
    ) -> list[dict[str, str]]:
        primary_owner = draft_session.owner_id or "Assigned operator"
        responsibilities = [
            {
                "role": "Process operator",
                "responsibility": (
                    "Execute the documented procedure in sequence, maintain data accuracy, "
                    "and complete required validations before final submission."
                ),
            },
            {
                "role": "Process owner",
                "responsibility": (
                    f"{primary_owner} remains accountable for document review, exception handling, "
                    "and approval of future updates to this SOP."
                ),
            },
        ]
        if applications:
            responsibilities.append(
                {
                    "role": "System/application support",
                    "responsibility": (
                        "Maintain application access, availability, and configuration for "
                        + ", ".join(applications)
                        + "."
                    ),
                }
            )
        return responsibilities

    @staticmethod
    def _build_sop_prerequisites(
        applications: list[str],
        process_notes: list[dict[str, Any]],
    ) -> list[str]:
        prerequisites = [
            f"Confirm user access to {application}."
            for application in applications
        ]
        if not prerequisites:
            prerequisites.append("Confirm access to the required source systems and records.")
        prerequisites.append("Review the latest source data or transaction inputs before starting the procedure.")
        if process_notes:
            prerequisites.append("Review documented notes, controls, and business constraints before execution.")
        return prerequisites

    @staticmethod
    def _build_sop_controls(process_notes: list[dict[str, Any]]) -> list[str]:
        controls = [
            str(note.get("text", "") or "").strip()
            for note in process_notes
            if str(note.get("text", "") or "").strip()
        ]
        if controls:
            return controls[:5]
        return [
            "Validate source data before performing the transaction.",
            "Review each major transition point before submission or save.",
        ]

    @staticmethod
    def _build_sop_expected_outcomes(
        process_sections: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
    ) -> list[str]:
        outcomes = [
            f"Each documented workflow section completes successfully: {section['title']}."
            for section in process_sections
            if section.get("title")
        ]
        if process_notes:
            outcomes.append("Supporting business constraints and notes are satisfied during execution.")
        if not outcomes:
            outcomes.append("The documented procedure completes successfully with the expected business result.")
        return outcomes[:5]

    def _build_sop_procedure_section(self, section: dict[str, Any]) -> dict[str, Any]:
        steps = section.get("steps", [])
        notes = section.get("notes", [])
        return {
            "title": section["title"],
            "summary": section["summary"],
            "objective": self._build_sop_section_objective(section["title"], steps),
            "steps": [
                {
                    "step_number": step["step_number"],
                    "instruction": step["action_text"],
                    "system": step.get("application_name", ""),
                    "source_data_note": step.get("source_data_note", ""),
                    "evidence_window": self._format_evidence_window(step),
                    "primary_screenshot_image": step.get("primary_screenshot_image", ""),
                    "has_primary_screenshot": step.get("has_primary_screenshot", False),
                }
                for step in steps
            ],
            "controls": [
                str(note.get("text", "") or "").strip()
                for note in notes
                if str(note.get("text", "") or "").strip()
            ],
            "diagram_image": section["diagram_image"],
            "diagram_rendered": section["diagram_rendered"],
        }

    @staticmethod
    def _build_sop_section_objective(title: str, steps: list[dict[str, Any]]) -> str:
        if steps:
            first_action = str(steps[0].get("action_text", "") or "").strip().rstrip(".")
            return f"Complete {title} by following the documented sequence beginning with {first_action}."
        return f"Complete the documented procedure for {title}."

    @staticmethod
    def _format_evidence_window(step: dict[str, Any]) -> str:
        start_timestamp = str(step.get("start_timestamp", "") or "").strip()
        end_timestamp = str(step.get("end_timestamp", "") or "").strip()
        timestamp = str(step.get("timestamp", "") or "").strip()
        if start_timestamp and end_timestamp:
            return f"{start_timestamp} to {end_timestamp}"
        return timestamp

    @staticmethod
    def _build_sop_evidence_summary(
        *,
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
        process_sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        screenshot_count = sum(
            1
            for step in process_steps
            if step.get("has_primary_screenshot")
        )
        return {
            "workflow_sections": len(process_sections),
            "procedural_steps": len(process_steps),
            "supporting_notes": len(process_notes),
            "primary_screenshots": screenshot_count,
        }


class BrdDocumentExportContextBuilder(SharedWorkflowExportContextBuilder, DocumentContextBuilder):
    """Build the BRD-specific render context from shared workflow primitives."""

    document_type = "brd"

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
        process_steps = shared_context["process_steps"]
        process_notes = shared_context["process_notes"]
        process_sections = shared_context["process_sections"]
        applications = SopDocumentExportContextBuilder._collect_unique_values(process_steps, "application_name")
        stakeholders = self._build_brd_stakeholders(draft_session, applications)
        requirements = self._build_brd_requirements(process_steps, process_notes, applications)
        business_rules = self._build_brd_business_rules(process_notes)
        assumptions = self._build_brd_assumptions(applications, process_sections)
        risks = self._build_brd_risks(process_notes)
        evidence_summary = self._build_brd_evidence_summary(process_steps, process_notes, process_sections)

        return {
            "session_title": draft_session.title,
            "owner_id": draft_session.owner_id,
            "process_steps": process_steps,
            "process_notes": process_notes,
            "process_sections": process_sections,
            "brd": {
                "title": draft_session.title,
                "owner_id": draft_session.owner_id,
                "session_id": draft_session.id,
                "status": draft_session.status,
                "generated_at": shared_context["generated_at"],
                "business_objective": (
                    f"Document the business requirements for {draft_session.title} "
                    "using the reviewed walkthrough evidence as the current-state baseline."
                ),
                "scope": SopDocumentExportContextBuilder._build_sop_scope(
                    draft_session.title,
                    process_sections,
                    process_steps,
                ),
                "current_state_summary": shared_context["process_summary"],
                "stakeholders": stakeholders,
                "applications": applications,
                "requirements": requirements,
                "business_rules": business_rules,
                "assumptions": assumptions,
                "risks_and_exceptions": risks,
                "workflow_sections": [
                    {
                        "title": section["title"],
                        "summary": section["summary"],
                        "step_count": len(section.get("steps", [])),
                        "steps": section.get("steps", []),
                        "notes": section.get("notes", []),
                    }
                    for section in process_sections
                ],
                "evidence_summary": evidence_summary,
            },
        }

    @staticmethod
    def _build_brd_stakeholders(
        draft_session: DraftSessionModel,
        applications: list[str],
    ) -> list[dict[str, str]]:
        stakeholders = [
            {
                "name": draft_session.owner_id or "Process owner",
                "role": "Process owner",
                "interest": "Approves the documented requirements and current-state interpretation.",
            },
            {
                "name": "Operational user",
                "role": "Business user",
                "interest": "Executes the workflow and relies on accurate procedural and system requirements.",
            },
        ]
        if applications:
            stakeholders.append(
                {
                    "name": ", ".join(applications),
                    "role": "System landscape",
                    "interest": "Provides the application context and integration boundaries for the business process.",
                }
            )
        return stakeholders

    @staticmethod
    def _build_brd_requirements(
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
        applications: list[str],
    ) -> list[dict[str, str]]:
        requirements: list[dict[str, str]] = []
        for index, step in enumerate(process_steps[:8], start=1):
            requirement_id = f"BR-{index:03d}"
            requirement_text = str(step.get("action_text", "") or "").strip()
            if not requirement_text:
                continue
            requirements.append(
                {
                    "id": requirement_id,
                    "category": "Functional",
                    "statement": f"The solution must support users to {requirement_text.lower().rstrip('.')}.",
                    "rationale": (
                        str(step.get("source_data_note", "") or "").strip()
                        or "Derived from the observed walkthrough step."
                    ),
                }
            )
        if applications:
            requirements.append(
                {
                    "id": f"BR-{len(requirements) + 1:03d}",
                    "category": "System",
                    "statement": "The solution must preserve access to the required application landscape.",
                    "rationale": "Observed process execution depends on " + ", ".join(applications) + ".",
                }
            )
        if process_notes:
            requirements.append(
                {
                    "id": f"BR-{len(requirements) + 1:03d}",
                    "category": "Control",
                    "statement": "The solution must enforce the documented business controls and validation steps.",
                    "rationale": "Derived from the supporting business rules and notes captured during review.",
                }
            )
        return requirements

    @staticmethod
    def _build_brd_business_rules(process_notes: list[dict[str, Any]]) -> list[str]:
        rules = [
            str(note.get("text", "") or "").strip()
            for note in process_notes
            if str(note.get("text", "") or "").strip()
        ]
        if rules:
            return rules[:8]
        return ["Business rules were not explicitly captured; validate rules with the process owner during review."]

    @staticmethod
    def _build_brd_assumptions(
        applications: list[str],
        process_sections: list[dict[str, Any]],
    ) -> list[str]:
        assumptions = [
            "The reviewed walkthrough reflects the intended current-state operating model.",
            "Required users have access to the necessary systems and source records.",
        ]
        if applications:
            assumptions.append("The documented process continues to rely on " + ", ".join(applications) + ".")
        if len(process_sections) > 1:
            assumptions.append("Workflow sections are reviewed independently but still form part of one business scenario.")
        return assumptions

    @staticmethod
    def _build_brd_risks(process_notes: list[dict[str, Any]]) -> list[str]:
        if process_notes:
            return [
                "Incomplete adherence to documented controls may cause data quality or compliance issues.",
                "Implicit business rules in the walkthrough should be validated before implementation decisions are finalized.",
            ]
        return [
            "Uncaptured exceptions or business rules may require follow-up validation with stakeholders.",
        ]

    @staticmethod
    def _build_brd_evidence_summary(
        process_steps: list[dict[str, Any]],
        process_notes: list[dict[str, Any]],
        process_sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "workflow_sections": len(process_sections),
            "observed_steps": len(process_steps),
            "captured_notes": len(process_notes),
        }


class DocumentExportContextBuilder(PddDocumentExportContextBuilder):
    """Backward-compatible alias for the current default PDD export builder."""
    pass
