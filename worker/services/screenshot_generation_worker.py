r"""
Purpose: Background worker for screenshot-only generation over persisted canonical steps.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\screenshot_generation_worker.py
"""

from __future__ import annotations

import json

from app.core.observability import bind_log_context, get_logger
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.models.action_log import ActionLogModel
from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.services.job_dispatcher import JobDispatcherService
from worker.bootstrap import get_db_session
from worker.services.draft_generation_stage_context import DraftGenerationContext
from worker.services.draft_generation_stage_services import PersistenceStage, ScreenshotDerivationStage

logger = get_logger(__name__)


class ScreenshotGenerationWorker:
    """Generate screenshots for the current canonical process without rebuilding the draft."""

    def __init__(self, task_id: str | None = None) -> None:
        self.task_id = task_id
        self.screenshot_stage = ScreenshotDerivationStage()
        self.persistence_stage = PersistenceStage()
        self.job_dispatcher = JobDispatcherService()

    def run(self, session_id: str) -> dict[str, int | str]:
        """Generate screenshots only for persisted canonical steps."""
        db = get_db_session()
        try:
            with bind_log_context(task_id=self.task_id, session_id=session_id):
                session = self._load_session(db, session_id)
                logger.info(
                    "Loaded draft session for screenshot generation",
                    extra={"event": "screenshot_generation.session_loaded"},
                )
                context = self._prepare_context(db, session)
                self.screenshot_stage.run(db, context)
                self.persistence_stage._persist_step_screenshots(db, context.persisted_step_models, context.all_steps)
                selected_screenshot_count = sum(len(step.get("_derived_screenshots", [])) for step in context.all_steps)
                db.add(
                    ActionLogModel(
                        session_id=session_id,
                        event_type="screenshots_generated",
                        title="Screenshots ready",
                        detail=f"{selected_screenshot_count} screenshots generated for canonical steps.",
                        actor="system",
                    )
                )
                db.commit()
                result = {
                    "session_id": session_id,
                    "screenshots_created": selected_screenshot_count,
                    "steps_updated": len(context.persisted_step_models),
                }
                logger.info(
                    "Persisted generated screenshots",
                    extra={"event": "screenshot_generation.persisted", **result},
                )
                return result
        except Exception:
            logger.exception("Screenshot generation pipeline failed", extra={"event": "screenshot_generation.failed"})
            raise
        finally:
            self.job_dispatcher.release_screenshot_generation_lock(session_id)
            db.close()

    def _load_session(self, db, session_id: str) -> DraftSessionModel:
        statement = (
            select(DraftSessionModel)
            .where(DraftSessionModel.id == session_id)
            .options(
                selectinload(DraftSessionModel.artifacts).selectinload(ArtifactModel.meeting),
                selectinload(DraftSessionModel.process_steps),
                selectinload(DraftSessionModel.process_notes),
            )
        )
        session = db.execute(statement).scalar_one_or_none()
        if session is None:
            raise ValueError(f"Draft session '{session_id}' was not found.")
        return session

    def _prepare_context(self, db, session: DraftSessionModel) -> DraftGenerationContext:
        transcript_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "transcript"]
        video_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "video"]
        if not transcript_artifacts:
            raise ValueError("No transcript artifacts found for screenshot generation.")
        if not video_artifacts:
            raise ValueError("No video artifacts found for screenshot generation.")
        if not session.process_steps:
            raise ValueError("No generated process steps are available for screenshot generation.")

        logger.info(
            "Preparing screenshot generation context",
            extra={
                "event": "screenshot_generation.preparing_context",
                "transcript_artifact_count": len(transcript_artifacts),
                "video_artifact_count": len(video_artifacts),
                "process_step_count": len(session.process_steps),
            },
        )

        step_ids = [step.id for step in session.process_steps]
        if step_ids:
            db.execute(delete(ProcessStepScreenshotModel).where(ProcessStepScreenshotModel.step_id.in_(step_ids)))
            db.execute(delete(ProcessStepScreenshotCandidateModel).where(ProcessStepScreenshotCandidateModel.step_id.in_(step_ids)))
        db.execute(delete(ArtifactModel).where(ArtifactModel.session_id == session.id, ArtifactModel.kind == "screenshot"))

        step_candidates: list[dict] = []
        steps_by_transcript: dict[str, list[dict]] = {}
        transcripts_by_meeting = self._transcripts_by_meeting(transcript_artifacts)
        preferred_transcripts_by_group_meeting = self._preferred_transcripts_by_group_meeting(session.process_steps)
        for step in sorted(session.process_steps, key=lambda item: item.step_number):
            evidence_references = self._strip_screenshot_evidence(step.evidence_references)
            step.evidence_references = json.dumps(evidence_references)
            step.screenshot_id = ""
            transcript_artifact_id = self._resolve_transcript_artifact_id(
                persisted_source_transcript_artifact_id=getattr(step, "source_transcript_artifact_id", None),
                evidence_references=evidence_references,
                meeting_id=step.meeting_id,
                process_group_id=step.process_group_id,
                transcripts_by_meeting=transcripts_by_meeting,
                preferred_transcripts_by_group_meeting=preferred_transcripts_by_group_meeting,
            )
            step_candidate = {
                "id": step.id,
                "process_group_id": step.process_group_id,
                "meeting_id": step.meeting_id,
                "step_number": step.step_number,
                "application_name": step.application_name,
                "action_text": step.action_text,
                "source_data_note": step.source_data_note,
                "timestamp": step.timestamp,
                "start_timestamp": step.start_timestamp,
                "end_timestamp": step.end_timestamp,
                "supporting_transcript_text": step.supporting_transcript_text,
                "screenshot_id": "",
                "confidence": step.confidence,
                "evidence_references": json.dumps(evidence_references),
                "edited_by_ba": step.edited_by_ba,
                "_transcript_artifact_id": transcript_artifact_id,
            }
            step_candidates.append(step_candidate)
            if transcript_artifact_id:
                steps_by_transcript.setdefault(transcript_artifact_id, []).append(step_candidate)

        db.commit()

        context = DraftGenerationContext(
            session_id=session.id,
            session=session,
            transcript_artifacts=transcript_artifacts,
            video_artifacts=video_artifacts,
            all_steps=step_candidates,
            all_notes=[],
            steps_by_transcript=steps_by_transcript,
        )
        context.persisted_step_models = list(sorted(session.process_steps, key=lambda item: item.step_number))  # type: ignore[attr-defined]
        logger.info(
            "Prepared screenshot generation context",
            extra={
                "event": "screenshot_generation.context_prepared",
                "steps_ready_for_screenshots": len(context.all_steps),
                "transcript_groups": len(context.steps_by_transcript),
            },
        )
        return context

    @staticmethod
    def _strip_screenshot_evidence(evidence_references_raw: str) -> list[dict]:
        try:
            parsed = json.loads(evidence_references_raw or "[]")
        except json.JSONDecodeError:
            parsed = []
        return [reference for reference in parsed if reference.get("kind") != "screenshot"]

    @staticmethod
    def _transcript_artifact_id(evidence_references: list[dict]) -> str | None:
        for reference in evidence_references:
            if reference.get("kind") == "transcript":
                artifact_id = reference.get("artifact_id")
                if isinstance(artifact_id, str) and artifact_id:
                    return artifact_id
        return None

    @staticmethod
    def _transcripts_by_meeting(transcript_artifacts: list[ArtifactModel]) -> dict[str, list[ArtifactModel]]:
        grouped: dict[str, list[ArtifactModel]] = {}
        for artifact in transcript_artifacts:
            meeting_id = getattr(artifact, "meeting_id", None)
            if not meeting_id:
                continue
            grouped.setdefault(meeting_id, []).append(artifact)
        for meeting_id, artifacts in grouped.items():
            grouped[meeting_id] = sorted(artifacts, key=lambda item: (getattr(item, "created_at", None), item.id))
        return grouped

    def _resolve_transcript_artifact_id(
        self,
        *,
        persisted_source_transcript_artifact_id: str | None,
        evidence_references: list[dict],
        meeting_id: str | None,
        process_group_id: str | None,
        transcripts_by_meeting: dict[str, list[ArtifactModel]],
        preferred_transcripts_by_group_meeting: dict[tuple[str, str], str],
    ) -> str | None:
        if persisted_source_transcript_artifact_id:
            return persisted_source_transcript_artifact_id
        if meeting_id and process_group_id:
            preferred = preferred_transcripts_by_group_meeting.get((meeting_id, process_group_id))
            if preferred:
                referenced = self._transcript_artifact_id(evidence_references)
                if referenced and referenced != preferred:
                    logger.info(
                        "Re-linked screenshot step to transcript from process-group lineage",
                        extra={
                            "event": "screenshot_generation.transcript_relinked",
                            "meeting_id": meeting_id,
                            "process_group_id": process_group_id,
                            "referenced_transcript_artifact_id": referenced,
                            "selected_transcript_artifact_id": preferred,
                        },
                    )
                return preferred
        if meeting_id:
            meeting_transcripts = transcripts_by_meeting.get(meeting_id, [])
            if len(meeting_transcripts) == 1:
                selected = meeting_transcripts[-1].id
                referenced = self._transcript_artifact_id(evidence_references)
                if referenced and referenced != selected:
                    logger.info(
                        "Re-linked screenshot step to transcript from persisted meeting lineage",
                        extra={
                            "event": "screenshot_generation.transcript_relinked",
                            "meeting_id": meeting_id,
                            "process_group_id": process_group_id,
                            "referenced_transcript_artifact_id": referenced,
                            "selected_transcript_artifact_id": selected,
                        },
                    )
                return selected
        return self._transcript_artifact_id(evidence_references)

    @staticmethod
    def _preferred_transcripts_by_group_meeting(process_steps: list[ProcessStepModel]) -> dict[tuple[str, str], str]:
        counts: dict[tuple[str, str], dict[str, int]] = {}
        for step in process_steps:
            if not step.meeting_id or not step.process_group_id:
                continue
            try:
                references = json.loads(step.evidence_references or "[]")
            except json.JSONDecodeError:
                references = []
            transcript_artifact_id = ScreenshotGenerationWorker._transcript_artifact_id(references)
            if not transcript_artifact_id:
                continue
            key = (step.meeting_id, step.process_group_id)
            bucket = counts.setdefault(key, {})
            bucket[transcript_artifact_id] = bucket.get(transcript_artifact_id, 0) + 1

        resolved: dict[tuple[str, str], str] = {}
        for key, bucket in counts.items():
            resolved[key] = sorted(bucket.items(), key=lambda item: (-item[1], item[0]))[0][0]
        return resolved
