from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProcessSummaryGenerationRequest:
    process_title: str
    workflow_summary: dict[str, object]
    steps: list[dict[str, object]]
    notes: list[dict[str, object]]
    document_type: str


@dataclass(slots=True)
class ProcessSummaryGenerationResponse:
    summary_text: str
    confidence: str = "unknown"
    rationale: str = ""
