from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class WorkflowGroupMatchRequest:
    transcript_name: str
    workflow_summary: dict[str, object]
    existing_groups: list[dict[str, object]] = field(default_factory=list)


@dataclass(slots=True)
class WorkflowGroupMatchResponse:
    matched_existing_title: str | None = None
    recommended_title: str = ""
    recommended_slug: str = ""
    confidence: str = "unknown"
    rationale: str = ""
