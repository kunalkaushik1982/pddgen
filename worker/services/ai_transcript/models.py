from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from worker.services.generation_types import NoteRecord, StepRecord


@dataclass
class TranscriptInterpretation:
    """Structured AI interpretation output."""

    steps: list[StepRecord]
    notes: list[NoteRecord]


@dataclass
class DiagramInterpretation:
    """Structured AI diagram output."""

    overview: dict[str, Any]
    detailed: dict[str, Any]


@dataclass
class ProcessGroupInterpretation:
    """Structured process-group classification output."""

    process_title: str
    canonical_slug: str
    matched_existing_title: str | None


@dataclass
class AmbiguousProcessGroupResolution:
    """Structured AI tie-break result for ambiguous process-group resolution."""

    matched_existing_title: str | None
    recommended_title: str
    recommended_slug: str
    confidence: str
    rationale: str


@dataclass
class WorkflowTitleInterpretation:
    """Structured AI workflow-title resolution output."""

    workflow_title: str
    canonical_slug: str
    confidence: str
    rationale: str


@dataclass
class WorkflowBoundaryInterpretation:
    """Structured AI workflow-boundary classification output."""

    decision: str
    confidence: str
    rationale: str


@dataclass
class WorkflowGroupMatchInterpretation:
    """Structured AI workflow-group matching output."""

    matched_existing_title: str | None
    recommended_title: str
    recommended_slug: str
    confidence: str
    rationale: str


@dataclass
class WorkflowSemanticEnrichmentInterpretation:
    """Structured AI semantic enrichment output for one evidence segment."""

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
    """Structured AI-generated business summary for one process group."""

    summary_text: str
    confidence: str
    rationale: str


@dataclass
class WorkflowCapabilityInterpretation:
    """Structured AI-generated capability tags for one workflow group."""

    capability_tags: list[str]
    confidence: str
    rationale: str

