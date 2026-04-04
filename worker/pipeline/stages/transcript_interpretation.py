from __future__ import annotations

from collections.abc import Sequence
from typing import Mapping, cast

from app.core.observability import bind_log_context, get_logger
from app.services.action_log_service import ActionLogService
from sqlalchemy.orm import Session
from app.services.step_extraction import StepExtractionService
from app.services.transcript_intelligence import TranscriptIntelligenceService
from worker.ai_skills.transcript_interpreter.interpreter import AITranscriptInterpreter
from worker.pipeline.stages.stage_context import DraftGenerationContext
from worker.pipeline.types import NoteRecord, StepRecord
from worker.media.transcript_normalizer import TranscriptNormalizer

logger = get_logger(__name__)


class FallbackTranscriptExtractor:
    """Heuristic step/note extractor used when the AI interpreter produces no output.

    SRP fix: extracted from TranscriptInterpretationStage so that the stage
    depends on one coherent extraction abstraction rather than two independent
    backend services injected separately.
    """

    def __init__(
        self,
        *,
        step_extractor: StepExtractionService,
        note_extractor: TranscriptIntelligenceService,
    ) -> None:
        self._step_extractor = step_extractor
        self._note_extractor = note_extractor

    def extract(
        self,
        *,
        transcript_artifact_id: str,
        transcript_text: str,
    ) -> tuple[list[StepRecord], list[NoteRecord]]:
        steps = [
            cast(StepRecord, step)
            for step in self._step_extractor.extract_steps(
                transcript_artifact_id=transcript_artifact_id,
                transcript_text=transcript_text,
            )
        ]
        notes = [
            cast(NoteRecord, note)
            for note in self._note_extractor.extract_notes(
                transcript_artifact_id=transcript_artifact_id,
                transcript_text=transcript_text,
            )
        ]
        return steps, notes


class TranscriptInterpretationStage:
    """Interpret transcripts into normalized steps and notes.

    SRP fix: fallback extraction is delegated to FallbackTranscriptExtractor,
    giving the stage a single clear job: coordinate interpretation per transcript.
    """

    def __init__(
        self,
        *,
        transcript_normalizer: TranscriptNormalizer,
        ai_transcript_interpreter: AITranscriptInterpreter,
        fallback_extractor: FallbackTranscriptExtractor,
        action_log_service: ActionLogService,
    ) -> None:
        self.transcript_normalizer = transcript_normalizer
        self.ai_transcript_interpreter = ai_transcript_interpreter
        self.fallback_extractor = fallback_extractor
        self.action_log_service = action_log_service

    def run(self, db: Session, context: DraftGenerationContext) -> None:
        from worker.pipeline.stages.support import extract_transcript_timestamps, timestamp_to_seconds

        with bind_log_context(stage="transcript_interpretation"):
            self.action_log_service.record(
                db,
                session_id=context.inputs.session_id,
                event_type="generation_stage",
                title="Interpreting transcript",
                detail=f"Processing {len(context.inputs.transcript_artifacts)} transcript artifact(s).",
                actor="system",
            )
            db.commit()

            for transcript in context.inputs.transcript_artifacts:
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
                    self._enrich_timestamps(typed_steps, normalized_text=normalized_text, timestamp_to_seconds=timestamp_to_seconds, extract_transcript_timestamps=extract_transcript_timestamps)
                    self._attach_context(typed_steps, typed_notes, transcript=transcript, context=context)
                    context.all_steps.extend(typed_steps)
                    context.steps_by_transcript.setdefault(transcript.id, []).extend(typed_steps)
                    context.all_notes.extend(typed_notes)
                    context.notes_by_transcript.setdefault(transcript.id, []).extend(typed_notes)
                    continue

                # AI produced no output — fall back to heuristic extraction.
                fallback_steps, fallback_notes = self.fallback_extractor.extract(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                )
                self._attach_context(fallback_steps, fallback_notes, transcript=transcript, context=context)
                context.all_steps.extend(fallback_steps)
                context.steps_by_transcript.setdefault(transcript.id, []).extend(fallback_steps)
                context.all_notes.extend(fallback_notes)
                context.notes_by_transcript.setdefault(transcript.id, []).extend(fallback_notes)

            logger.info(
                "Transcript interpretation completed",
                extra={"event": "draft_generation.stage_completed", "step_count": len(context.all_steps), "note_count": len(context.all_notes)},
            )

    @staticmethod
    def _enrich_timestamps(steps: list[StepRecord], *, normalized_text: str, timestamp_to_seconds, extract_transcript_timestamps) -> None:  # type: ignore[no-untyped-def]
        transcript_timestamps = extract_transcript_timestamps(normalized_text)
        for index, step in enumerate(steps):
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

    @staticmethod
    def _attach_context(steps: list[StepRecord], notes: list[NoteRecord], *, transcript, context: DraftGenerationContext) -> None:  # type: ignore[no-untyped-def]
        for step in steps:
            step["_transcript_artifact_id"] = transcript.id
            step["process_group_id"] = context.default_process_group_id
            step["meeting_id"] = getattr(transcript, "meeting_id", None)
        for note in notes:
            note["_transcript_artifact_id"] = transcript.id
            note["process_group_id"] = context.default_process_group_id
            note["meeting_id"] = getattr(transcript, "meeting_id", None)

    @staticmethod
    def _coerce_step_records(steps: Sequence[Mapping[str, object]]) -> list[StepRecord]:
        return [cast(StepRecord, step) for step in steps]

    @staticmethod
    def _coerce_note_records(notes: Sequence[Mapping[str, object]]) -> list[NoteRecord]:
        return [cast(NoteRecord, note) for note in notes]
