from __future__ import annotations

from app.models.artifact import ArtifactModel
from worker.pipeline.types import NoteRecord, StepRecord


def sort_transcripts(transcript_artifacts: list[ArtifactModel]) -> list[ArtifactModel]:
    return sorted(transcript_artifacts, key=transcript_sort_key)


def transcript_sort_key(artifact: ArtifactModel) -> tuple[int, str, str, str]:
    meeting = getattr(artifact, "meeting", None)
    order_index = getattr(meeting, "order_index", None)
    meeting_date = getattr(meeting, "meeting_date", None)
    uploaded_at = getattr(meeting, "uploaded_at", None) or getattr(artifact, "created_at", None)
    return (
        order_index if order_index is not None else 1_000_000,
        meeting_date.isoformat() if meeting_date is not None else "",
        uploaded_at.isoformat() if uploaded_at is not None else "",
        artifact.id,
    )


def step_transcript_id(step: StepRecord) -> str | None:
    transcript_id = step.get("_transcript_artifact_id")
    return transcript_id if isinstance(transcript_id, str) and transcript_id else None


def note_transcript_id(note: NoteRecord) -> str | None:
    transcript_id = note.get("_transcript_artifact_id")
    return transcript_id if isinstance(transcript_id, str) and transcript_id else None


def transcript_process_group_id(
    transcript_id: str,
    *,
    steps_by_transcript: dict[str, list[StepRecord]],
    notes_by_transcript: dict[str, list[NoteRecord]],
) -> str | None:
    for step in steps_by_transcript.get(transcript_id, []):
        process_group_id = step.get("process_group_id")
        if isinstance(process_group_id, str) and process_group_id:
            return process_group_id
    for note in notes_by_transcript.get(transcript_id, []):
        process_group_id = note.get("process_group_id")
        if isinstance(process_group_id, str) and process_group_id:
            return process_group_id
    return None


def group_transcripts_by_process_group(
    *,
    transcript_artifacts: list[ArtifactModel],
    steps_by_transcript: dict[str, list[StepRecord]],
    notes_by_transcript: dict[str, list[NoteRecord]],
) -> dict[str, list[ArtifactModel]]:
    grouped: dict[str, list[ArtifactModel]] = {}
    for transcript in sort_transcripts(transcript_artifacts):
        process_group_id = transcript_process_group_id(
            transcript.id,
            steps_by_transcript=steps_by_transcript,
            notes_by_transcript=notes_by_transcript,
        )
        if process_group_id is None:
            continue
        grouped.setdefault(process_group_id, []).append(transcript)
    return grouped
