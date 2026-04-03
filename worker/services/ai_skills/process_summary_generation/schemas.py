from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from collections.abc import Sequence


@dataclass(slots=True)
class ProcessSummaryGenerationRequest:
    process_title: str
    workflow_summary: dict[str, object]
    steps: Sequence[Mapping[str, object]]
    notes: Sequence[Mapping[str, object]]
    document_type: str


@dataclass(slots=True)
class ProcessSummaryGenerationResponse:
    summary_text: str
    confidence: str = "unknown"
    rationale: str = ""
