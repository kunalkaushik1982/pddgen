from __future__ import annotations

from worker.ai_skills.transcript_to_steps.schemas import TranscriptToStepsResponse
from worker.ai_skills.transcript_interpreter.models import TranscriptInterpretation
from worker.ai_skills.transcript_interpreter.normalization import normalize_note, normalize_step


def build_legacy_transcript_interpretation(
    *,
    transcript_artifact_id: str,
    skill_result: TranscriptToStepsResponse,
) -> TranscriptInterpretation:
    steps = [
        normalize_step(
            {
                "application_name": item.application_name,
                "action_text": item.action_text,
                "source_data_note": item.source_data_note,
                "start_timestamp": item.start_timestamp,
                "end_timestamp": item.end_timestamp,
                "display_timestamp": item.display_timestamp,
                "supporting_transcript_text": item.supporting_transcript_text,
                "confidence": item.confidence,
            },
            transcript_artifact_id,
        )
        for item in skill_result.steps
    ]
    notes = [
        normalize_note(
            {
                "text": item.text,
                "confidence": item.confidence,
                "inference_type": item.inference_type,
            }
        )
        for item in skill_result.notes
    ]
    return TranscriptInterpretation(steps=steps, notes=notes)
