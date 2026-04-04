from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WorkflowBoundaryDetectionRequest:
    left_segment: dict[str, object]
    right_segment: dict[str, object]


@dataclass(slots=True)
class WorkflowBoundaryDetectionResponse:
    decision: str
    confidence: str
    rationale: str
