from __future__ import annotations

from collections.abc import Sequence
from typing import Mapping, cast

from app.core.observability import bind_log_context, get_logger
from app.services.action_log_service import ActionLogService
from app.services.step_extraction import StepExtractionService
from app.services.transcript_intelligence import TranscriptIntelligenceService
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
from worker.services.draft_generation.stage_context import DraftGenerationContext
from worker.services.generation_types import NoteRecord, StepRecord
from worker.services.media.transcript_normalizer import TranscriptNormalizer

logger = get_logger(__name__)


class TranscriptInterpretationStage:
    """Interpret transcripts into normalized steps and notes."""

    def __init__(
        self,
        *,
        transcript_normalizer: TranscriptNormalizer | None = None,
        ai_transcript_interpreter: AITranscriptInterpreter | None = None,
        step_extractor: StepExtractionService | None = None,
        note_extractor: TranscriptIntelligenceService | None = None,
        action_log_service: ActionLogService | None = None,
    ) -> None:
        self.transcript_normalizer = transcript_normalizer or TranscriptNormalizer()
        self.ai_transcript_interpreter = ai_transcript_interpreter or AITranscriptInterpreter()
        self.step_extractor = step_extractor or StepExtractionService()
        self.note_extractor = note_extractor or TranscriptIntelligenceService()
        self.action_log_service = action_log_service or ActionLogService()

    def run(self, db, context: DraftGenerationContext) -> None:  # type: ignore[no-untyped-def]
        from worker.services.draft_generation.support import extract_transcript_timestamps, timestamp_to_seconds

        with bind_log_context(stage="transcript_interpretation"):
            self.action_log_service.record(
                db,
                session_id=context.session_id,
                event_type="generation_stage",
                title="Interpreting transcript",
                detail=f"Processing {len(context.transcript_artifacts)} transcript artifact(s).",
                actor="system",
            )
            db.commit()

            for transcript in context.transcript_artifacts:
                normalized_text = context.normalized_transcripts.get(transcript.id)
                if normalized_text is None:
                    normalized_text = self.transcript_normalizer.normalize(transcript.storage_path, transcript.name)
                    context.normalized_transcripts[transcript.id] = normalized_text
                interpretation = self.ai_transcript_interpreter.interpret(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                )

                if interpretation is not None and interpretation.steps:
                    typed_steps = self._coerce_step_records(interpretation.steps)
                    typed_notes = self._coerce_note_records(interpretation.notes)
                    transcript_timestamps = extract_transcript_timestamps(normalized_text)
                    for index, step in enumerate(typed_steps):
                        inferred_start = transcript_timestamps[index] if index < len(transcript_timestamps) else (transcript_timestamps[-1] if transcript_timestamps else "")
                        inferred_end = transcript_timestamps[index + 1] if transcript_timestamps and (index + 1) < len(transcript_timestamps) else inferred_start
                        if not str(step.get("start_timestamp", "") or ""):
                            step["start_timestamp"] = inferred_start
                        if not str(step.get("end_timestamp", "") or ""):
                            step["end_timestamp"] = inferred_end
                        if not str(step.get("timestamp", "") or ""):
                            step["timestamp"] = step["start_timestamp"]
                        if not str(step.get("supporting_transcript_text", "") or ""):
                            step["supporting_transcript_text"] = step.get("action_text", "")
                        if timestamp_to_seconds(step["end_timestamp"]) < timestamp_to_seconds(step["start_timestamp"]):
                            step["end_timestamp"] = step["start_timestamp"]
                        step["_transcript_artifact_id"] = transcript.id
                        step["process_group_id"] = context.default_process_group_id
                        step["meeting_id"] = getattr(transcript, "meeting_id", None)
                    context.all_steps.extend(typed_steps)
                    context.steps_by_transcript.setdefault(transcript.id, []).extend(typed_steps)
                    for note in typed_notes:
                        note["_transcript_artifact_id"] = transcript.id
                        note["process_group_id"] = context.default_process_group_id
                        note["meeting_id"] = getattr(transcript, "meeting_id", None)
                    context.all_notes.extend(typed_notes)
                    context.notes_by_transcript.setdefault(transcript.id, []).extend(typed_notes)
                    continue

                transcript_steps = self._coerce_step_records(self.step_extractor.extract_steps(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                ))
                for step in transcript_steps:
                    step["_transcript_artifact_id"] = transcript.id
                    step["process_group_id"] = context.default_process_group_id
                    step["meeting_id"] = getattr(transcript, "meeting_id", None)
                context.all_steps.extend(transcript_steps)
                context.steps_by_transcript.setdefault(transcript.id, []).extend(transcript_steps)
                transcript_notes = self._coerce_note_records(self.note_extractor.extract_notes(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                ))
                for note in transcript_notes:
                    note["_transcript_artifact_id"] = transcript.id
                    note["process_group_id"] = context.default_process_group_id
                    note["meeting_id"] = getattr(transcript, "meeting_id", None)
                context.all_notes.extend(transcript_notes)
                context.notes_by_transcript.setdefault(transcript.id, []).extend(transcript_notes)

            logger.info(
                "Transcript interpretation completed",
                extra={"event": "draft_generation.stage_completed", "step_count": len(context.all_steps), "note_count": len(context.all_notes)},
            )

    @staticmethod
    def _coerce_step_records(steps: Sequence[Mapping[str, object]]) -> list[StepRecord]:
        return [cast(StepRecord, step) for step in steps]

    @staticmethod
    def _coerce_note_records(notes: Sequence[Mapping[str, object]]) -> list[NoteRecord]:
        return [cast(NoteRecord, note) for note in notes]
