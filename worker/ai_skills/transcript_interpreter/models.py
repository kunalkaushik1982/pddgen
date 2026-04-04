from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from worker.pipeline.types import NoteRecord, StepRecord


@dataclass
class TranscriptInterpretation:
    steps: list[StepRecord]
    notes: list[NoteRecord]


@dataclass
class DiagramInterpretation:
    overview: dict[str, Any]
    detailed: dict[str, Any]


@dataclass
class ProcessGroupInterpretation:
    process_title: str
    canonical_slug: str
    matched_existing_title: str | None


@dataclass
class AmbiguousProcessGroupResolution:
    matched_existing_title: str | None
    recommended_title: str
    recommended_slug: str
    confidence: str
    rationale: str


@dataclass
class WorkflowTitleInterpretation:
    workflow_title: str
    canonical_slug: str
    confidence: str
    rationale: str


@dataclass
class WorkflowBoundaryInterpretation:
    decision: str
    confidence: str
    rationale: str


@dataclass
class WorkflowGroupMatchInterpretation:
    matched_existing_title: str | None
    recommended_title: str
    recommended_slug: str
    confidence: str
    rationale: str


@dataclass
class WorkflowSemanticEnrichmentInterpretation:
    actor: str | None
    actor_role: str | None
    system_name: str | None
    action_verb: str | None
    action_type: str | None
    business_object: str | None
    workflow_goal: str | None
    rule_hints: list[str]
    domain_terms: list[str]
    confidence: str
    rationale: str


@dataclass
class ProcessSummaryInterpretation:
    summary_text: str
    confidence: str
    rationale: str


@dataclass
class WorkflowCapabilityInterpretation:
    capability_tags: list[str]
    confidence: str
    rationale: str
