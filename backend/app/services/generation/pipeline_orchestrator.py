r"""
Purpose: Service for coordinating extraction, enrichment, and review state generation.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\pipeline_orchestrator.py
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.portability.job_messaging.locks.redis_lock import build_redis_distributed_lock
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.action_log import ActionLogModel
from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.meeting_evidence_bundle import MeetingEvidenceBundleModel
from app.models.process_group import ProcessGroupModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.services.generation.screenshot_mapping import ScreenshotMappingService
from app.services.generation.step_extraction import StepExtractionService
from app.services.generation.transcript_intelligence import TranscriptIntelligenceService
from app.services.draft_session.process_group_service import ProcessGroupService
from app.storage.storage_service import StorageService


class PipelineOrchestratorService:
    """Coordinate pipeline stages for building the draft session."""

    def __init__(
        self,
        *,
        storage_service: StorageService,
        step_extraction_service: StepExtractionService,
        transcript_intelligence_service: TranscriptIntelligenceService,
        screenshot_mapping_service: ScreenshotMappingService,
        process_group_service: ProcessGroupService,
    ) -> None:
        self.storage_service = storage_service
        self.step_extraction_service = step_extraction_service
        self.transcript_intelligence_service = transcript_intelligence_service
        self.screenshot_mapping_service = screenshot_mapping_service
        self.process_group_service = process_group_service

    @staticmethod
    def reconcile_stale_draft_generation_processing_if_needed(db: Session, session: DraftSessionModel) -> None:
        """If draft generation died after marking timing complete, or hung past threshold, unblock the session."""
        if session.status != "processing":
            return
        settings = get_settings()
        threshold = float(settings.draft_generation_stale_after_seconds or 0.0)
        now = datetime.now(timezone.utc)

        completed = session.draft_generation_completed_at
        if completed is not None:
            if completed.tzinfo is None:
                completed = completed.replace(tzinfo=timezone.utc)
            # Worker exited (timing finally ran) but status was never moved off processing.
            if (now - completed).total_seconds() > 15:
                PipelineOrchestratorService._finalize_stale_draft_generation(
                    db,
                    session,
                    "Draft generation ended abnormally; session was left in processing. Click Generate to retry.",
                )
            return

        if threshold <= 0:
            return
        started = session.draft_generation_started_at
        if started is None:
            return
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if (now - started).total_seconds() <= threshold:
            return
        PipelineOrchestratorService._finalize_stale_draft_generation(
            db,
            session,
            "Draft generation did not finish in time (worker may have stopped). Click Generate to retry.",
        )

    @staticmethod
    def _finalize_stale_draft_generation(db: Session, session: DraftSessionModel, detail: str) -> None:
        session.status = "failed"
        db.add(
            ActionLogModel(
                session_id=session.id,
                event_type="generation_failed",
                title="Draft generation stalled",
                detail=detail[:500],
                actor="system",
            )
        )
        db.commit()
        try:
            lock = build_redis_distributed_lock(get_settings())
            lock.release(f"pdd-generator:draft-generation-lock:{session.id}")
        except Exception:
            pass

    @staticmethod
    def reconcile_stale_screenshot_processing_if_needed(db: Session, session: DraftSessionModel) -> None:
        """If a screenshot run died while status was still processing, return the session to review."""
        if session.status != "processing":
            return
        settings = get_settings()
        threshold = settings.screenshot_extraction_stale_after_seconds
        if threshold <= 0:
            return
        stage_log = next(
            (
                item
                for item in sorted(session.action_logs, key=lambda action_log: action_log.created_at, reverse=True)
                if item.event_type == "generation_stage"
                and item.title.strip().lower() == "extracting screenshots"
            ),
            None,
        )
        if stage_log is None:
            return
        created = stage_log.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - created).total_seconds() <= threshold:
            return
        session.status = "review"
        db.add(
            ActionLogModel(
                session_id=session.id,
                event_type="screenshot_generation_failed",
                title="Screenshot run stalled",
                detail=(
                    "The screenshot worker did not report completion in time. "
                    "Session returned to review; click Generate SS to retry."
                ),
                actor="system",
            )
        )
        db.commit()

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
        self.reconcile_stale_draft_generation_processing_if_needed(db, session)
        self.reconcile_stale_screenshot_processing_if_needed(db, session)
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

    def mark_session_screenshot_processing(self, db: Session, session_id: str, owner_id: str | None = None) -> DraftSessionModel:
        """Mark session as processing for screenshot-only background work (draft already in review)."""
        session = self.get_session(db, session_id, owner_id=owner_id)
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
