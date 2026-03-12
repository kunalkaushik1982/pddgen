r"""
Purpose: Service for deterministic DOCX template rendering.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_renderer.py
"""

import json
from datetime import datetime
from pathlib import Path

from docxtpl import DocxTemplate
from docxtpl import InlineImage
from docx.shared import Mm
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.draft_session import DraftSessionModel
from app.models.output_document import OutputDocumentModel
from app.storage.storage_service import StorageService


class DocumentRendererService:
    """Render reviewed structured draft data into a DOCX document."""

    def __init__(self, storage_service: StorageService | None = None) -> None:
        self.storage_service = storage_service or StorageService()
        self.settings = get_settings()

    def render_docx(self, db: Session, draft_session: DraftSessionModel) -> OutputDocumentModel:
        """Render a DOCX document from the draft session."""
        template_artifact = next((artifact for artifact in draft_session.artifacts if artifact.kind == "template"), None)
        if template_artifact is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A template artifact is required before export.",
            )

        template_path = Path(template_artifact.storage_path)
        if not template_path.exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template file was not found on storage.")

        output_name = f"{draft_session.id}_draft.docx"
        output_path = self.settings.local_storage_root / draft_session.id / self.settings.docx_output_folder / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = DocxTemplate(str(template_path))
        doc.render(self._build_context(draft_session, doc))
        doc.save(str(output_path))

        output_document = OutputDocumentModel(
            session_id=draft_session.id,
            kind="docx",
            storage_path=str(output_path),
        )
        db.add(output_document)
        draft_session.status = "exported"
        db.commit()
        db.refresh(output_document)
        return output_document

    def _build_context(self, draft_session: DraftSessionModel, template_document: DocxTemplate) -> dict:
        """Build the DOCX template context from the session."""
        screenshot_map = {
            artifact.id: artifact
            for artifact in draft_session.artifacts
            if artifact.kind == "screenshot"
        }
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

        return {
            # Legacy keys kept for backward compatibility with earlier template experiments.
            "session_title": draft_session.title,
            "owner_id": draft_session.owner_id,
            "process_steps": process_steps,
            "process_notes": process_notes,
            # Preferred template contract.
            "pdd": {
                "title": draft_session.title,
                "owner_id": draft_session.owner_id,
                "session_id": draft_session.id,
                "status": draft_session.status,
                "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "step_count": len(process_steps),
                "note_count": len(process_notes),
                "overview": {
                    "process_name": draft_session.title,
                    "document_owner": draft_session.owner_id,
                    "document_status": draft_session.status,
                    "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                },
                "as_is_steps": process_steps,
                "business_rules": process_notes,
            },
        }

    def _build_step_context(self, step, screenshot_map: dict, template_document: DocxTemplate) -> dict:
        """Build one DOCX context block for a process step."""
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
            "screenshot_path": primary_screenshot_path,
            "screenshot_image": self._build_inline_image(template_document, primary_screenshot_path),
            "screenshots": screenshot_items,
        }

    @staticmethod
    def _resolve_screenshot_path(screenshot_id: str, screenshot_map: dict) -> str:
        """Resolve a screenshot file path for a step if available."""
        if not screenshot_id:
            return ""
        artifact = screenshot_map.get(screenshot_id)
        if artifact is None:
            return ""
        path = Path(artifact.storage_path)
        return str(path) if path.exists() else ""

    @staticmethod
    def _build_inline_image(template_document: DocxTemplate, screenshot_path: str):
        """Build a template image object when a screenshot file exists."""
        if not screenshot_path:
            return ""
        try:
            return InlineImage(template_document, screenshot_path, width=Mm(140))
        except Exception:
            return ""
