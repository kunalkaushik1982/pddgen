from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WorkflowCapabilityTaggingRequest:
    process_title: str
    workflow_summary: dict[str, object]
    document_type: str


@dataclass(slots=True)
class WorkflowCapabilityTaggingResponse:
    capability_tags: list[str]
    confidence: str = "unknown"
    rationale: str = ""
