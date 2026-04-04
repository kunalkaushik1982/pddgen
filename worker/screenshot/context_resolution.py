from __future__ import annotations

import json

from app.models.artifact import ArtifactModel
from app.models.process_step import ProcessStepModel


def transcript_artifact_id(evidence_references: list[dict]) -> str | None:
    for reference in evidence_references:
        if reference.get("kind") == "transcript":
            artifact_id = reference.get("artifact_id")
            if isinstance(artifact_id, str) and artifact_id:
                return artifact_id
    return None


def transcripts_by_meeting(transcript_artifacts: list[ArtifactModel]) -> dict[str, list[ArtifactModel]]:
    grouped: dict[str, list[ArtifactModel]] = {}
    for artifact in transcript_artifacts:
        meeting_id = getattr(artifact, "meeting_id", None)
        if not meeting_id:
            continue
        grouped.setdefault(meeting_id, []).append(artifact)
    for meeting_id, artifacts in grouped.items():
        grouped[meeting_id] = sorted(artifacts, key=lambda item: (getattr(item, "created_at", None), item.id))
    return grouped


def preferred_transcripts_by_group_meeting(process_steps: list[ProcessStepModel]) -> dict[tuple[str, str], str]:
    counts: dict[tuple[str, str], dict[str, int]] = {}
    for step in process_steps:
        if not step.meeting_id or not step.process_group_id:
            continue
        try:
            references = json.loads(step.evidence_references or "[]")
        except json.JSONDecodeError:
            references = []
        resolved_transcript_artifact_id = transcript_artifact_id(references)
        if not resolved_transcript_artifact_id:
            continue
        key = (step.meeting_id, step.process_group_id)
        bucket = counts.setdefault(key, {})
        bucket[resolved_transcript_artifact_id] = bucket.get(resolved_transcript_artifact_id, 0) + 1
    resolved: dict[tuple[str, str], str] = {}
    for key, bucket in counts.items():
        resolved[key] = sorted(bucket.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return resolved


def resolve_transcript_artifact_id(
    *,
    persisted_source_transcript_artifact_id: str | None,
    evidence_references: list[dict],
    meeting_id: str | None,
    process_group_id: str | None,
    transcripts_by_meeting_map: dict[str, list[ArtifactModel]],
    preferred_transcripts_by_group_meeting_map: dict[tuple[str, str], str],
) -> str | None:
    if persisted_source_transcript_artifact_id:
        return persisted_source_transcript_artifact_id
    if meeting_id and process_group_id:
        preferred = preferred_transcripts_by_group_meeting_map.get((meeting_id, process_group_id))
        if preferred:
            return preferred
    if meeting_id:
        meeting_transcripts = transcripts_by_meeting_map.get(meeting_id, [])
        if len(meeting_transcripts) == 1:
            return meeting_transcripts[-1].id
    return transcript_artifact_id(evidence_references)
