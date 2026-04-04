from __future__ import annotations

import re

from app.models.artifact import ArtifactModel
from worker.pipeline.types import StepRecord

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


def signature_tokens(steps: list[StepRecord]) -> set[str]:
    text = " ".join(str(step.get("action_text", "") or "") for step in steps[:12])
    tokens = [token for token in normalize_text(text).split() if token and token not in STOPWORDS]
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {token for token, _ in ordered[:5]}


def operation_signature_from_steps(steps: list[StepRecord]) -> list[str]:
    signature: list[str] = []
    seen: set[str] = set()
    for step in steps[:8]:
        action_text = str(step.get("action_text", "") or "").strip()
        if not action_text:
            continue
        normalized = normalize_text(action_text)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        signature.append(action_text)
        if len(signature) >= 5:
            break
    return signature
