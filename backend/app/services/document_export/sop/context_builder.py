r"""
SOP export: procedure-oriented context from session evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate
from sqlalchemy.orm import Session

from app.models.draft_session import DraftSessionModel
from app.services.documents.document_context_builder_interfaces import DocumentContextBuilder
from app.services.document_export.enrichment.store import merge_enrichment_into_sop_purpose
from app.services.document_export.pdd.context_builder import PddDocumentExportContextBuilder
from app.storage.storage_service import StorageService


class SopDocumentExportContextBuilder(PddDocumentExportContextBuilder):
    """Build the SOP-specific render context from shared workflow primitives (same AS-IS narrative as PDD for sections)."""

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
        multi_process = len(process_sections) > 1

        applications = self.collect_unique_values(process_steps, "application_name")
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

        purpose = (
            f"This SOP defines the observed operating procedure for {draft_session.title} "
            "using the reviewed walkthrough evidence as the source of truth."
        )
        purpose = merge_enrichment_into_sop_purpose(draft_session, purpose)
        scope = self._build_sop_scope(draft_session.title, process_sections, process_steps)

        process_document_blocks: list[dict[str, Any]] = []
        if multi_process:
            process_document_blocks = [
                self._build_sop_process_document_block(
                    draft_session,
                    section=section,
                )
                for section in process_sections
            ]

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
                "diagram_type": getattr(draft_session, "diagram_type", None) or "flowchart",
                "generated_at": shared_context["generated_at"],
                "multi_process": multi_process,
                "process_document_blocks": process_document_blocks,
                "purpose": purpose,
                "scope": scope if not multi_process else "",
                "applications": applications if not multi_process else [],
                "prerequisites": prerequisites if not multi_process else [],
                "responsibilities": responsibilities if not multi_process else [],
                "controls": controls if not multi_process else [],
                "expected_outcomes": expected_outcomes if not multi_process else [],
                "procedure_sections": procedure_sections if not multi_process else [],
                "supporting_notes": process_notes if not multi_process else [],
                "evidence_summary": evidence_summary if not multi_process else {},
                "procedure_step_count": len(process_steps),
                "procedure_section_count": len(procedure_sections) if not multi_process else 0,
                "supporting_note_count": len(process_notes) if not multi_process else 0,
            },
        }

    def _build_sop_process_document_block(
        self,
        draft_session: DraftSessionModel,
        *,
        section: dict[str, Any],
    ) -> dict[str, Any]:
        """One full SOP procedure body scoped to a single workflow section / process group."""
        process_steps = section["steps"]
        process_notes = section["notes"]
        applications = self.collect_unique_values(process_steps, "application_name")
        prerequisites = self._build_sop_prerequisites(applications, process_notes)
        responsibilities = self._build_sop_responsibilities(draft_session, applications)
        controls = self._build_sop_controls(process_notes)
        expected_outcomes = self._build_sop_expected_outcomes([section], process_notes)
        procedure_sections = [self._build_sop_procedure_section(section)]
        evidence_summary = self._build_sop_evidence_summary(
            process_steps=process_steps,
            process_notes=process_notes,
            process_sections=[section],
        )
        purpose = (
            f"This SOP defines the observed operating procedure for {draft_session.title} "
            "using the reviewed walkthrough evidence as the source of truth."
        )
        scope = self._build_sop_scope(draft_session.title, [section], process_steps)
        return {
            "process_title": str(section.get("title") or draft_session.title),
            "purpose": purpose,
            "scope": scope,
            "applications": applications,
            "prerequisites": prerequisites,
            "responsibilities": responsibilities,
            "controls": controls,
            "expected_outcomes": expected_outcomes,
            "procedure_sections": procedure_sections,
            "evidence_summary": evidence_summary,
            "supporting_notes": process_notes,
        }

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
