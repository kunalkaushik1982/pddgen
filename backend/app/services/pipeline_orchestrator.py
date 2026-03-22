r"""
Purpose: Service for coordinating extraction, enrichment, and review state generation.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\pipeline_orchestrator.py
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.meeting_evidence_bundle import MeetingEvidenceBundleModel
from app.models.process_group import ProcessGroupModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.services.screenshot_mapping import ScreenshotMappingService
from app.services.step_extraction import StepExtractionService
from app.services.transcript_intelligence import TranscriptIntelligenceService
from app.services.process_group_service import ProcessGroupService
from app.storage.storage_service import StorageService


class PipelineOrchestratorService:
    """Coordinate pipeline stages for building the draft session."""

    def __init__(
        self,
        storage_service: StorageService | None = None,
        step_extraction_service: StepExtractionService | None = None,
        transcript_intelligence_service: TranscriptIntelligenceService | None = None,
        screenshot_mapping_service: ScreenshotMappingService | None = None,
    ) -> None:
        self.storage_service = storage_service or StorageService()
        self.step_extraction_service = step_extraction_service or StepExtractionService()
        self.transcript_intelligence_service = transcript_intelligence_service or TranscriptIntelligenceService()
        self.screenshot_mapping_service = screenshot_mapping_service or ScreenshotMappingService()
        self.process_group_service = ProcessGroupService()

    def get_session(self, db: Session, session_id: str, owner_id: str | None = None) -> DraftSessionModel:
        """Load a draft session with related entities."""
        statement = (
            select(DraftSessionModel)
            .where(DraftSessionModel.id == session_id)
            .options(
                selectinload(DraftSessionModel.artifacts),
                selectinload(DraftSessionModel.action_logs),
                selectinload(DraftSessionModel.diagram_layouts),
                selectinload(DraftSessionModel.meetings),
                selectinload(DraftSessionModel.meeting_evidence_bundles).selectinload(MeetingEvidenceBundleModel.meeting),
                selectinload(DraftSessionModel.process_groups),
                selectinload(DraftSessionModel.process_steps).selectinload(ProcessStepModel.step_screenshots).selectinload(ProcessStepScreenshotModel.artifact),
                selectinload(DraftSessionModel.process_steps).selectinload(ProcessStepModel.step_screenshot_candidates).selectinload(ProcessStepScreenshotCandidateModel.artifact),
                selectinload(DraftSessionModel.process_notes),
                selectinload(DraftSessionModel.output_documents),
            )
        )
        session = db.execute(statement).scalar_one_or_none()
        if session is None or (owner_id is not None and session.owner_id != owner_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft session not found.")
        self.process_group_service.ensure_default_process_group(db, session=session)
        return session

    def mark_session_processing(self, db: Session, session_id: str, owner_id: str | None = None) -> DraftSessionModel:
        """Validate draft-generation prerequisites and mark the session as processing."""
        session = self.get_session(db, session_id, owner_id=owner_id)
        transcript_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "transcript"]
        template_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "template"]

        if not transcript_artifacts:
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="At least one transcript artifact is required before generation.",
          )
        if not template_artifacts:
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="A template artifact is required before generation.",
          )
        if session.status == "processing":
            return session

        session.status = "processing"
        db.commit()
        return self.get_session(db, session_id, owner_id=owner_id)

    def run_draft_generation(self, db: Session, session_id: str) -> DraftSessionModel:
        """Generate process steps and notes from available transcript artifacts."""
        session = self.get_session(db, session_id)
        transcript_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "transcript"]
        if not transcript_artifacts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one transcript artifact is required before generation.",
            )

        screenshot_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "screenshot"]
        process_group = self.process_group_service.ensure_default_process_group(db, session=session)
        db.query(ProcessStepModel).filter(ProcessStepModel.session_id == session_id).delete()
        db.query(ProcessNoteModel).filter(ProcessNoteModel.session_id == session_id).delete()

        all_steps: list[dict] = []
        all_notes: list[dict] = []

        for transcript in transcript_artifacts:
            transcript_text = self.storage_service.read_text(transcript.storage_path)
            all_steps.extend(
                self.step_extraction_service.extract_steps(
                    transcript_artifact_id=transcript.id,
                    transcript_text=transcript_text,
                )
            )
            all_notes.extend(
                self.transcript_intelligence_service.extract_notes(
                    transcript_artifact_id=transcript.id,
                    transcript_text=transcript_text,
                )
            )

        for step in all_steps:
            step["process_group_id"] = process_group.id
        for note in all_notes:
            note["process_group_id"] = process_group.id

        for step_number, step in enumerate(all_steps, start=1):
            step["step_number"] = step_number

        mapped_steps = self.screenshot_mapping_service.attach_uploaded_screenshots(
            steps=all_steps,
            screenshot_artifacts=screenshot_artifacts,
        )

        db.add_all(ProcessStepModel(session_id=session_id, **step) for step in mapped_steps)
        db.add_all(ProcessNoteModel(session_id=session_id, **note) for note in all_notes)
        session.status = "review"
        db.commit()
        return self.get_session(db, session_id)

    def delete_draft_session(self, db: Session, session_id: str, owner_id: str | None = None) -> None:
        """Delete one draft-only session and its stored artifacts."""
        session = self.get_session(db, session_id, owner_id=owner_id)
        if session.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft sessions can be deleted from Workspace.",
            )

        storage_paths = {
            artifact.storage_path
            for artifact in session.artifacts
            if artifact.storage_path
        }
        storage_paths.update(
            output.storage_path
            for output in session.output_documents
            if output.storage_path
        )

        for storage_path in storage_paths:
            try:
                self.storage_service.delete(storage_path)
            except Exception:
                continue

        db.delete(session)
        db.commit()
