from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SemanticEnrichmentRequest:
    transcript_name: str
    segment_text: str
    segment_context: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SemanticEnrichmentResponse:
    actor: str | None = None
    actor_role: str | None = None
    system_name: str | None = None
    action_verb: str | None = None
    action_type: str | None = None
    business_object: str | None = None
    workflow_goal: str | None = None
    rule_hints: list[str] = field(default_factory=list)
    domain_terms: list[str] = field(default_factory=list)
    confidence: str = "unknown"
    rationale: str = ""
