from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DiagramGenerationRequest:
    session_title: str
    diagram_type: str
    steps: list[dict[str, object]]
    notes: list[dict[str, object]]


@dataclass(slots=True)
class DiagramGenerationResponse:
    overview: dict[str, object]
    detailed: dict[str, object]
