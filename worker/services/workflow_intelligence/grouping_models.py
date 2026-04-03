from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from app.models.process_group import ProcessGroupModel


class CandidateMatchRecord(TypedDict, total=False):
    group_title: str
    score: float | str
    title_ratio: float
    signature_overlap: float
    profile_overlap: float
    system_alignment: float
    application_alignment: float


class HeuristicGroupMatchResult(TypedDict):
    matched_group: ProcessGroupModel | None
    best_score: float
    ambiguity: bool
    candidate_matches: list[CandidateMatchRecord]
    supporting_signals: list[str]


@dataclass(slots=True)
class ProcessGroupingResult:
    process_groups: list[ProcessGroupModel]
    transcript_group_ids: dict[str, str]
    assignment_details: list[dict[str, object]]


@dataclass(slots=True)
class TranscriptWorkflowProfile:
    """Aggregated workflow-intelligence signals for one transcript artifact."""

    transcript_artifact_id: str
    top_actors: list[str]
    top_objects: list[str]
    top_systems: list[str]
    top_actions: list[str]
    top_goals: list[str]
    top_rules: list[str]
    top_applications: list[str] = field(default_factory=list)
    top_domain_terms: list[str] = field(default_factory=list)
    boundary_to_next: str | None = None
    boundary_to_next_confidence: str | None = None


@dataclass(slots=True)
class GroupResolutionDecision:
    """Explain how one transcript was assigned to a workflow group."""

    inferred_title: str
    inferred_slug: str
    matched_group: ProcessGroupModel | None
    decision: str
    confidence: str
    decision_source: str
    is_ambiguous: bool
    rationale: str
    candidate_matches: list[CandidateMatchRecord]
    supporting_signals: list[str]
    heuristic_decision: str | None = None
    heuristic_confidence: str | None = None
    ai_decision: str | None = None
    ai_confidence: str | None = None
    conflict_detected: bool = False


__all__ = [
    "CandidateMatchRecord",
    "GroupResolutionDecision",
    "HeuristicGroupMatchResult",
    "ProcessGroupingResult",
    "TranscriptWorkflowProfile",
]
