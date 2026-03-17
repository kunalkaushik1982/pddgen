r"""
Purpose: Service for deterministic DOCX template rendering.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_renderer.py
"""

import json
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from docxtpl import DocxTemplate
from docxtpl import InlineImage
from docx.shared import Mm
from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.diagram_layout import DiagramLayoutModel
from app.models.output_document import OutputDocumentModel
from app.services.process_diagram_service import ProcessDiagramService
from app.storage.storage_service import StorageService


class DocumentRendererService:
    """Render reviewed structured draft data into a DOCX document."""
    _pdf_conversion_lock = threading.Lock()

    def __init__(self, storage_service: StorageService | None = None) -> None:
        self.storage_service = storage_service or StorageService()
        self.settings = get_settings()
        self.process_diagram_service = ProcessDiagramService()

    def render_docx(self, db: Session, draft_session: DraftSessionModel) -> OutputDocumentModel:
        """Render a DOCX document from the draft session."""
        output_path = self._build_output_path(draft_session, "docx")
        self._render_docx_file(db, draft_session, output_path)

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

    def render_pdf(self, db: Session, draft_session: DraftSessionModel) -> OutputDocumentModel:
        """Render a PDF by converting the same DOCX content used for Word export."""
        output_path = self._build_output_path(draft_session, "pdf")
        with TemporaryDirectory(prefix=f"pdd_{draft_session.id}_") as temp_dir:
            temp_docx_path = Path(temp_dir) / f"{draft_session.id}_draft.docx"
            self._render_docx_file(db, draft_session, temp_docx_path)
            self._convert_docx_to_pdf(temp_docx_path, output_path)

        output_document = OutputDocumentModel(
            session_id=draft_session.id,
            kind="pdf",
            storage_path=str(output_path),
        )
        db.add(output_document)
        draft_session.status = "exported"
        db.commit()
        db.refresh(output_document)
        return output_document

    def _get_template_path(self, draft_session: DraftSessionModel) -> Path:
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

    def _build_output_path(self, draft_session: DraftSessionModel, extension: str) -> Path:
        output_name = f"{draft_session.id}_draft.{extension}"
        output_path = self.settings.local_storage_root / draft_session.id / self.settings.docx_output_folder / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    def _render_docx_file(self, db: Session, draft_session: DraftSessionModel, output_path: Path) -> None:
        template_path = self._get_template_path(draft_session)
        doc = DocxTemplate(str(template_path))
        doc.render(self._build_context(db, draft_session, doc))
        doc.save(str(output_path))

    def _convert_docx_to_pdf(self, source_docx_path: Path, output_pdf_path: Path) -> None:
        conversion_errors: list[str] = []
        if self._convert_with_docx2pdf(source_docx_path, output_pdf_path, conversion_errors):
            return
        if self._convert_with_libreoffice(source_docx_path, output_pdf_path, conversion_errors):
            return

        error_suffix = f" Conversion details: {' | '.join(conversion_errors)}" if conversion_errors else ""
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "PDF export requires DOCX-to-PDF conversion support. "
                "Install Microsoft Word with the 'docx2pdf' package, or install LibreOffice and expose 'soffice' in PATH."
                f"{error_suffix}"
            ).strip(),
        )

    def _convert_with_docx2pdf(
        self,
        source_docx_path: Path,
        output_pdf_path: Path,
        conversion_errors: list[str],
    ) -> bool:
        try:
            from docx2pdf import convert
        except ImportError as error:
            conversion_errors.append(f"docx2pdf import failed: {error}")
            return False

        pythoncom = None
        com_initialized = False
        try:
            import pythoncom  # type: ignore

            pythoncom.CoInitialize()
            com_initialized = True
        except ImportError:
            pythoncom = None
        except Exception as error:
            conversion_errors.append(f"COM initialization failed: {error}")
            return False

        attempts = 2
        try:
            with self._pdf_conversion_lock:
                for attempt in range(1, attempts + 1):
                    try:
                        if output_pdf_path.exists():
                            output_pdf_path.unlink()
                        convert(str(source_docx_path), str(output_pdf_path))
                        if output_pdf_path.exists():
                            return True
                        conversion_errors.append(
                            f"docx2pdf attempt {attempt} completed without producing '{output_pdf_path.name}'"
                        )
                    except Exception as error:
                        conversion_errors.append(f"docx2pdf attempt {attempt} failed: {error}")
                    if attempt < attempts:
                        time.sleep(1.0)
            return False
        finally:
            if pythoncom is not None and com_initialized:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

    def _convert_with_libreoffice(
        self,
        source_docx_path: Path,
        output_pdf_path: Path,
        conversion_errors: list[str],
    ) -> bool:
        soffice_path = shutil.which("soffice")
        if not soffice_path:
            conversion_errors.append("LibreOffice 'soffice' not found in PATH")
            return False

        try:
            subprocess.run(
                [
                    soffice_path,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(output_pdf_path.parent),
                    str(source_docx_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as error:
            conversion_errors.append(f"LibreOffice conversion failed: {error}")
            return False

        generated_pdf = output_pdf_path.parent / f"{source_docx_path.stem}.pdf"
        if generated_pdf.exists() and generated_pdf != output_pdf_path:
            generated_pdf.replace(output_pdf_path)
        if not output_pdf_path.exists():
            conversion_errors.append("LibreOffice completed without producing the expected PDF output")
        return output_pdf_path.exists()

    def _build_context(self, db: Session, draft_session: DraftSessionModel, template_document: DocxTemplate) -> dict:
        """Build the DOCX template context from the session."""
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
                "diagram_type": draft_session.diagram_type,
                "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "step_count": len(process_steps),
                "note_count": len(process_notes),
                "step_bullets": [step["bullet_entry"] for step in process_steps],
                "overview": {
                    "process_name": draft_session.title,
                    "document_owner": draft_session.owner_id,
                    "document_status": draft_session.status,
                    "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "process_summary": process_summary,
                },
                "as_is_steps": process_steps,
                "to_be_recommendations": to_be_recommendations,
                "process_flow": {
                    "mermaid_source": diagram_source,
                    "diagram_source": diagram_source,
                    "diagram_path": str(detailed_diagram_path) if detailed_diagram_path else "",
                    "diagram_image": self._build_process_diagram_image(
                        template_document,
                        str(detailed_diagram_path) if detailed_diagram_path else "",
                    ),
                    "detailed_path": str(detailed_diagram_path) if detailed_diagram_path else "",
                    "detailed_image": self._build_process_diagram_image(
                        template_document,
                        str(detailed_diagram_path) if detailed_diagram_path else "",
                    ),
                    "rendered": bool(detailed_diagram_path),
                },
                "business_rules": process_notes,
            },
        }

    @staticmethod
    def _build_process_summary(draft_session: DraftSessionModel, process_steps: list[dict], process_notes: list[dict]) -> str:
        """Build a business-readable overview paragraph for the exported document."""
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
            if len(note_samples) == 1:
                note_text = note_samples[0]
            else:
                note_text = " and ".join(note_samples)
            summary_parts.append(
                f"During the walkthrough, additional business context was also identified, including {note_text}, which helps explain the intent, dependencies, and control expectations behind the recorded steps."
            )

        summary_parts.append(
            "This section should be used as a narrative summary of the current-state process before reviewing the detailed step bullets, primary screenshots, and supporting process flow diagram."
        )

        return " ".join(summary_parts)

    @staticmethod
    def _load_saved_diagram_positions(db: Session, session_id: str, view_type: str) -> dict[str, dict[str, float | str]]:
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

    @staticmethod
    def _build_process_diagram_image(template_document: DocxTemplate, diagram_path: str):
        """Build a fitted DOCX image for overview or detailed diagrams."""
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



