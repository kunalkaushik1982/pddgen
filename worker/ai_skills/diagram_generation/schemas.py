from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from collections.abc import Sequence


@dataclass(slots=True)
class DiagramGenerationRequest:
    session_title: str
    diagram_type: str
    steps: Sequence[Mapping[str, object]]
    notes: Sequence[Mapping[str, object]]


@dataclass(slots=True)
class DiagramGenerationResponse:
    overview: dict[str, object]
    detailed: dict[str, object]
