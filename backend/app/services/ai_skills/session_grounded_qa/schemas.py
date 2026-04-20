from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SessionGroundedQARequest:
    session_id: str
    session_title: str
    process_group_id: str | None
    question: str
    evidence: list[dict[str, str]]


@dataclass(slots=True)
class SessionGroundedQAResponse:
    answer: str
    confidence: str = "medium"
    citation_ids: list[str] = field(default_factory=list)
