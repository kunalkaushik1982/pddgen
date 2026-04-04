r"""
Purpose: Assign transcript outputs into logical process groups within a session.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\grouping\grouping_service.py
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import TypedDict, cast

from app.core.observability import get_logger
from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.process_group import ProcessGroupModel
from app.services.process_group_service import ProcessGroupService
from worker.ai_skills.process_summary_generation.schemas import ProcessSummaryGenerationRequest
from worker.ai_skills.registry import AISkillRegistry
from worker.ai_skills.workflow_capability_tagging.schemas import WorkflowCapabilityTaggingRequest
from worker.ai_skills.workflow_group_match.schemas import WorkflowGroupMatchRequest
from worker.ai_skills.workflow_title_resolution.schemas import WorkflowTitleResolutionRequest
from worker.grouping.grouping_ai_adapters import (
    InterpreterProcessSummarySkill,
    InterpreterWorkflowCapabilityTaggingSkill,
    InterpreterWorkflowGroupMatchSkill,
    InterpreterWorkflowTitleResolutionSkill,
)
from worker.grouping.grouping_titles import (
    fallback_title,
    normalize_workflow_title,
    preferred_workflow_suffix,
    starts_with_non_business_action,
)
from worker.grouping.grouping_assignment_flow import assign_groups
from worker.grouping.grouping_identity_flow import (
    match_existing_group_with_ai,
    resolve_ambiguity,
    resolve_group_identity,
    resolve_title_with_ai,
)
from worker.grouping.grouping_models import (
    CandidateMatchRecord,
    GroupResolutionDecision,
    HeuristicGroupMatchResult,
    ProcessGroupingResult,
    TranscriptWorkflowProfile,
)
from worker.grouping.grouping_profiles import (
    STOPWORDS,
    build_transcript_profiles,
    extract_leading_action_verb,
    merge_profile_lists,
    normalize_text,
    profile_tokens,
    sort_transcripts,
)
from worker.grouping.grouping_decisions import (
    build_ai_group_match_decision,
    build_heuristic_group_decision,
    heuristic_resolution_confidence,
    resolve_ambiguity_with_ai,
)
from worker.grouping.grouping_matching import (
    application_alignment_score,
    has_explicit_tool_mismatch,
    match_existing_group,
    system_alignment_score,
)
from worker.grouping.grouping_summaries import (
    build_group_workflow_summary,
    build_process_summary_fallback,
    build_workflow_summary,
    group_summary_seed,
    normalize_capability_tags,
    operation_signature_from_steps,
    parse_capability_tags,
    signature_tokens,
    to_capability_label,
)
from worker.grouping.grouping_summary_refresh import (
    fallback_capability_tags,
    refresh_group_summaries,
    resolve_capability_tags,
    serialize_existing_groups_for_ai,
)
from worker.grouping.grouping_text import slugify
from worker.ai_skills.transcript_interpreter.interpreter import (
    AITranscriptInterpreter,
    WorkflowGroupMatchInterpretation,
    WorkflowTitleInterpretation,
)
from worker.pipeline.types import NoteRecord, StepRecord
from . import EvidenceSegment, WorkflowBoundaryDecision

logger = get_logger(__name__)


class ProcessGroupingService:
    """Cluster transcript outputs into same-process vs different-process groups.

    SRP: public API is assign_groups(). Internal stages delegate to standalone
    functions in adjacent modules — no private wrapper methods.
    OCP: constants are sourced from grouping_titles (single source of truth).
    DIP: AISkillRegistry is injected, not constructed internally.
    """

    _ACCEPTED_AI_CONFIDENCE = {"high", "medium"}
    # OCP fix: import from the single source of truth instead of duplicating.
    _STOPWORDS = STOPWORDS

    def __init__(
        self,
        *,
        process_group_service: ProcessGroupService,
        ai_transcript_interpreter: AITranscriptInterpreter,
        ai_skill_registry: AISkillRegistry,
    ) -> None:
        self.process_group_service = process_group_service
        self.ai_transcript_interpreter = ai_transcript_interpreter
        self._ai_skill_registry = ai_skill_registry
        self._workflow_title_resolution_skill = InterpreterWorkflowTitleResolutionSkill(self.ai_transcript_interpreter)
        self._workflow_group_match_skill = InterpreterWorkflowGroupMatchSkill(self.ai_transcript_interpreter)
        self._process_summary_generation_skill = InterpreterProcessSummarySkill(self.ai_transcript_interpreter)
        self._workflow_capability_tagging_skill = InterpreterWorkflowCapabilityTaggingSkill(self.ai_transcript_interpreter)

    def assign_groups(
        self,
        *,
        db,
        session: DraftSessionModel,
        transcript_artifacts: list[ArtifactModel],
        steps_by_transcript: dict[str, list[StepRecord]],
        notes_by_transcript: dict[str, list[NoteRecord]],
        evidence_segments: list[EvidenceSegment] | None = None,
        workflow_boundary_decisions: list[WorkflowBoundaryDecision] | None = None,
    ) -> ProcessGroupingResult:
        return assign_groups(
            self,
            db=db,
            session=session,
            transcript_artifacts=transcript_artifacts,
            steps_by_transcript=steps_by_transcript,
            notes_by_transcript=notes_by_transcript,
            evidence_segments=evidence_segments,
            workflow_boundary_decisions=workflow_boundary_decisions,
        )
