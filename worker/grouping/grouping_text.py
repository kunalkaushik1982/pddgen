from __future__ import annotations

import re

from app.models.artifact import ArtifactModel

STOPWORDS = {
    "a", "an", "and", "the", "to", "of", "for", "in", "on", "with", "into", "from", "then",
    "after", "before", "click", "select", "enter", "open", "go", "navigate", "screen", "field",
    "data", "details", "form", "tab", "save", "submit", "create", "creation", "process",
}


def normalize_text(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s-]+", " ", value.lower())
    collapsed = re.sub(r"\s+", "-", normalized.strip())
    return re.sub(r"-{2,}", "-", collapsed).strip("-") or "process"


def extract_leading_action_verb(action_text: str) -> str:
    match = re.match(r"^\s*([a-z]+(?:\s+[a-z]+)?)", action_text.lower())
    return match.group(1).strip() if match else ""


def sort_transcripts(transcript_artifacts: list[ArtifactModel]) -> list[ArtifactModel]:
    return sorted(
        transcript_artifacts,
        key=lambda artifact: (
            meeting.order_index
            if (meeting := getattr(artifact, "meeting", None)) is not None and meeting.order_index is not None
            else 1_000_000,
            meeting_date.isoformat()
            if (meeting := getattr(artifact, "meeting", None)) is not None
            and (meeting_date := getattr(meeting, "meeting_date", None)) is not None
            else "",
            uploaded_at.isoformat()
            if (meeting := getattr(artifact, "meeting", None)) is not None
            and (uploaded_at := getattr(meeting, "uploaded_at", None)) is not None
            else "",
            artifact.id,
        ),
    )
