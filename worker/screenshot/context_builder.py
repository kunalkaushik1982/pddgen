from __future__ import annotations

from worker import bootstrap as _bootstrap  # noqa: F401

from worker.pipeline.stages.stage_context import DraftGenerationContext
from worker.pipeline.types import StepRecord
from worker.screenshot.context_cleanup import reset_screenshot_state, strip_screenshot_evidence
from worker.screenshot.context_resolution import (
    preferred_transcripts_by_group_meeting,
    resolve_transcript_artifact_id,
    transcripts_by_meeting,
)


class DefaultScreenshotContextBuilder:
    def build(self, db, session) -> DraftGenerationContext:  # type: ignore[no-untyped-def]
        transcript_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "transcript"]
        video_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "video"]
        if not transcript_artifacts:
            raise ValueError("No transcript artifacts found for screenshot generation.")
        if not video_artifacts:
            raise ValueError("No video artifacts found for screenshot generation.")
        if not session.process_steps:
            raise ValueError("No generated process steps are available for screenshot generation.")

        reset_screenshot_state(db, session=session)

        step_candidates: list[StepRecord] = []
        steps_by_transcript: dict[str, list[StepRecord]] = {}
        transcripts_by_meeting_map = transcripts_by_meeting(transcript_artifacts)
        preferred_transcripts_by_group_meeting_map = preferred_transcripts_by_group_meeting(session.process_steps)
        for step in sorted(session.process_steps, key=lambda item: item.step_number):
            evidence_references = strip_screenshot_evidence(step.evidence_references)
            step.evidence_references = __import__("json").dumps(evidence_references)
            step.screenshot_id = ""
            resolved_transcript_artifact_id = resolve_transcript_artifact_id(
                persisted_source_transcript_artifact_id=getattr(step, "source_transcript_artifact_id", None),
                evidence_references=evidence_references,
                meeting_id=step.meeting_id,
                process_group_id=step.process_group_id,
                transcripts_by_meeting_map=transcripts_by_meeting_map,
                preferred_transcripts_by_group_meeting_map=preferred_transcripts_by_group_meeting_map,
            )
            step_candidate: StepRecord = {
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
                "evidence_references": __import__("json").dumps(evidence_references),
                "edited_by_ba": step.edited_by_ba,
                "_transcript_artifact_id": resolved_transcript_artifact_id,
            }
            step_candidates.append(step_candidate)
            if resolved_transcript_artifact_id:
                steps_by_transcript.setdefault(resolved_transcript_artifact_id, []).append(step_candidate)

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
        context.persisted_step_models = list(sorted(session.process_steps, key=lambda item: item.step_number))
        return context
