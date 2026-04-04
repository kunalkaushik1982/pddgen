from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WorkflowTitleResolutionRequest:
    transcript_name: str
    workflow_summary: dict[str, object]


@dataclass(slots=True)
class WorkflowTitleResolutionResponse:
    workflow_title: str
    canonical_slug: str
    confidence: str = "unknown"
    rationale: str = ""
