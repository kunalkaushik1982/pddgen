r"""
Purpose: Assign transcript outputs into logical process groups within a session.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\process_grouping_service.py
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
from worker.ai_skills.registry import AISkillRegistry, build_default_ai_skill_registry
from worker.ai_skills.workflow_capability_tagging.schemas import WorkflowCapabilityTaggingRequest
from worker.ai_skills.workflow_group_match.schemas import WorkflowGroupMatchRequest
from worker.ai_skills.workflow_title_resolution.schemas import WorkflowTitleResolutionRequest
from worker.grouping.grouping_ai_adapters import (
    InterpreterProcessSummarySkill,
    InterpreterWorkflowCapabilityTaggingSkill,
    InterpreterWorkflowGroupMatchSkill,
    InterpreterWorkflowTitleResolutionSkill,
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
try:
    from worker.grouping.grouping_matching import (
        application_alignment_score,
        has_explicit_tool_mismatch,
        match_existing_group,
        system_alignment_score,
    )
except Exception:  # pragma: no cover - isolated-loader compatibility
    from difflib import SequenceMatcher

    def system_alignment_score(*, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str], normalize_text):  # type: ignore[no-untyped-def]
        if not workflow_profile.top_systems:
            return 0.0
        normalized_systems = {normalize_text(value) for value in workflow_profile.top_systems if value}
        if not normalized_systems:
            return 0.0
        if any(system in " ".join(group_tokens) for system in normalized_systems):
            return 1.0
        return -0.5

    def application_alignment_score(*, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str], normalize_text):  # type: ignore[no-untyped-def]
        if not workflow_profile.top_applications:
            return 0.0
        normalized_applications = {normalize_text(value) for value in workflow_profile.top_applications if value}
        if not normalized_applications:
            return 0.0
        if any(application in " ".join(group_tokens) for application in normalized_applications):
            return 1.0
        return -0.75

    def has_explicit_tool_mismatch(*, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str], normalize_text):  # type: ignore[no-untyped-def]
        tool_markers = [normalize_text(value) for value in [*workflow_profile.top_systems, *workflow_profile.top_applications] if value]
        if len(tool_markers) == 0:
            return False
        normalized_group_text = " ".join(group_tokens)
        return all(marker not in normalized_group_text for marker in tool_markers)

    def match_existing_group(*, slug: str, title: str, steps: list[StepRecord], workflow_profile: TranscriptWorkflowProfile, existing_groups: list[ProcessGroupModel], normalize_text, stopwords: set[str], signature_tokens) -> HeuristicGroupMatchResult:  # type: ignore[no-untyped-def]
        for group in existing_groups:
            if slug and group.canonical_slug == slug:
                return cast(HeuristicGroupMatchResult, {"matched_group": group, "best_score": 1.0, "ambiguity": False, "candidate_matches": [{"group_title": group.title, "score": 1.0}], "supporting_signals": ["canonical_slug_match"]})
        normalized_title = normalize_text(title)
        candidate_signature = signature_tokens(steps)
        profile_tokens = {token for token in normalize_text(" ".join([*workflow_profile.top_actors, *workflow_profile.top_objects, *workflow_profile.top_systems, *workflow_profile.top_applications, *workflow_profile.top_actions, *workflow_profile.top_goals, *workflow_profile.top_rules, *workflow_profile.top_domain_terms])).split() if token and token not in stopwords}
        best_group: ProcessGroupModel | None = None
        best_score = 0.0
        second_best_score = 0.0
        candidate_scores: list[CandidateMatchRecord] = []
        for group in existing_groups:
            title_ratio = SequenceMatcher(None, normalized_title, normalize_text(group.title)).ratio()
            signature_overlap = 0.0
            system_alignment = 0.0
            application_alignment = 0.0
            group_tokens: set[str] = set()
            if getattr(group, "summary_text", ""):
                group_tokens = {token for token in normalize_text(group.summary_text).split() if token and token not in stopwords}
                signature_overlap = len(candidate_signature & group_tokens) / max(len(candidate_signature | group_tokens), 1)
                profile_overlap = len(profile_tokens & group_tokens) / max(len(profile_tokens | group_tokens), 1) if profile_tokens else 0.0
                system_alignment = system_alignment_score(workflow_profile=workflow_profile, group_tokens=group_tokens, normalize_text=normalize_text)
                application_alignment = application_alignment_score(workflow_profile=workflow_profile, group_tokens=group_tokens, normalize_text=normalize_text)
            else:
                profile_overlap = 0.0
            score = (title_ratio * 0.35) + (signature_overlap * 0.18) + (profile_overlap * 0.12) + (system_alignment * 0.15) + (application_alignment * 0.2)
            if has_explicit_tool_mismatch(workflow_profile=workflow_profile, group_tokens=group_tokens, normalize_text=normalize_text):
                score -= 0.25
            candidate_scores.append({"group_title": group.title, "score": round(score, 3), "title_ratio": round(title_ratio, 3), "signature_overlap": round(signature_overlap, 3), "profile_overlap": round(profile_overlap, 3), "system_alignment": round(system_alignment, 3), "application_alignment": round(application_alignment, 3)})
            if score > best_score:
                second_best_score = best_score
                best_score = score
                best_group = group
            elif score > second_best_score:
                second_best_score = score
        candidate_scores.sort(key=lambda item: float(item.get("score", 0.0) or 0.0), reverse=True)
        ambiguity = best_score >= 0.72 and second_best_score >= 0.7 and abs(best_score - second_best_score) <= 0.15
        supporting_signals = []
        if best_score >= 0.82:
            supporting_signals.append("strong_existing_group_match")
        elif best_score >= 0.72:
            supporting_signals.append("moderate_existing_group_match")
        if ambiguity:
            supporting_signals.append("competing_group_candidates")
        return cast(HeuristicGroupMatchResult, {"matched_group": best_group if best_score >= 0.86 else None, "best_score": best_score, "ambiguity": ambiguity, "candidate_matches": candidate_scores[:3], "supporting_signals": supporting_signals})
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
try:
    from worker.grouping.grouping_title_support import (
        fallback_title,
        normalize_workflow_title,
        preferred_workflow_suffix,
        starts_with_non_business_action,
    )
except Exception:  # pragma: no cover - isolated-loader compatibility
    NON_BUSINESS_ACTIONS_FALLBACK = {
        "open", "go", "go to", "goto", "navigate", "launch", "login", "log in", "select", "click", "enter",
    }
    WORKFLOW_SUFFIX_BY_ACTION_FALLBACK = {
        "create": "Creation", "submit": "Creation", "save": "Creation", "update": "Maintenance", "edit": "Maintenance",
        "change": "Maintenance", "maintain": "Maintenance", "review": "Review", "approve": "Approval",
        "validate": "Validation", "check": "Validation", "reconcile": "Reconciliation", "post": "Posting",
    }

    def starts_with_non_business_action(title: str) -> bool:
        lowered = title.lower().strip()
        return any(lowered.startswith(f"{action} ") or lowered == action for action in NON_BUSINESS_ACTIONS_FALLBACK)

    def preferred_workflow_suffix(*, steps: list[StepRecord], workflow_profile: TranscriptWorkflowProfile, extract_leading_action_verb):  # type: ignore[no-untyped-def]
        action_candidates = [*workflow_profile.top_actions]
        action_candidates.extend(extract_leading_action_verb(str(step.get("action_text", "") or "")) for step in steps[:8])
        for action in action_candidates:
            if not action:
                continue
            normalized_action = action.lower().strip()
            if normalized_action in NON_BUSINESS_ACTIONS_FALLBACK:
                continue
            suffix = WORKFLOW_SUFFIX_BY_ACTION_FALLBACK.get(normalized_action)
            if suffix:
                return suffix
        return "Creation" if workflow_profile.top_objects else "Process"

    def normalize_workflow_title(*, base_title: str, steps: list[StepRecord], workflow_profile: TranscriptWorkflowProfile):  # type: ignore[no-untyped-def]
        normalized_title = re.sub(r"\s+", " ", (base_title or "").strip()).title()
        object_name = workflow_profile.top_objects[0].title() if workflow_profile.top_objects else ""
        preferred_suffix_value = preferred_workflow_suffix(
            steps=steps,
            workflow_profile=workflow_profile,
            extract_leading_action_verb=extract_leading_action_verb,
        )
        if object_name:
            if preferred_suffix_value and not normalized_title.endswith(preferred_suffix_value):
                if starts_with_non_business_action(normalized_title) or object_name.lower() in normalized_title.lower():
                    return f"{object_name} {preferred_suffix_value}".strip()
            if starts_with_non_business_action(normalized_title):
                return f"{object_name} {preferred_suffix_value or 'Process'}".strip()
        if preferred_suffix_value and normalized_title and not normalized_title.endswith(preferred_suffix_value):
            if starts_with_non_business_action(normalized_title):
                return f"{normalized_title.split()[-1].title()} {preferred_suffix_value}".strip()
        return normalized_title or "Process"

    def fallback_title(*, transcript: ArtifactModel, steps: list[StepRecord], workflow_profile: TranscriptWorkflowProfile, normalize_text, extract_leading_action_verb):  # type: ignore[no-untyped-def]
        if workflow_profile.top_goals:
            normalized_goal_title = normalize_workflow_title(base_title=workflow_profile.top_goals[0], steps=steps, workflow_profile=workflow_profile)
            if normalized_goal_title:
                return normalized_goal_title
        if workflow_profile.top_objects:
            object_name = workflow_profile.top_objects[0]
            action_name = workflow_profile.top_actions[0] if workflow_profile.top_actions else None
            normalized_object_title = normalize_workflow_title(base_title=f"{object_name} {action_name}".strip() if action_name else object_name, steps=steps, workflow_profile=workflow_profile)
            if normalized_object_title:
                return normalized_object_title
        combined = " ".join([transcript.name, *[str(step.get("action_text", "") or "") for step in steps[:8]], *[str(step.get("supporting_transcript_text", "") or "") for step in steps[:3]]])
        normalized = normalize_text(combined)
        for pattern in [r"\b(sales order(?: creation)?)\b", r"\b(purchase order(?: creation)?)\b", r"\b(goods receipt)\b", r"\b(invoice(?: creation| posting)?)\b"]:
            match = re.search(pattern, normalized)
            if match:
                return normalize_workflow_title(base_title=match.group(1).title(), steps=steps, workflow_profile=workflow_profile)
        signature = list(signature_tokens(steps))
        if signature:
            phrase = " ".join(signature[:3]).strip()
            if phrase:
                normalized_signature_title = normalize_workflow_title(base_title=phrase.title(), steps=steps, workflow_profile=workflow_profile)
                if normalized_signature_title:
                    return normalized_signature_title
        transcript_title = transcript.name.rsplit(".", 1)[0].strip() or "Process"
        return normalize_workflow_title(base_title=transcript_title, steps=steps, workflow_profile=workflow_profile)
from worker.ai_skills.transcript_interpreter.interpreter import (
    AITranscriptInterpreter,
    WorkflowGroupMatchInterpretation,
    WorkflowTitleInterpretation,
)
from worker.pipeline.types import NoteRecord, StepRecord
from worker.grouping import EvidenceSegment, WorkflowBoundaryDecision

logger = get_logger(__name__)


class ProcessGroupingService:
    """Cluster transcript outputs into same-process vs different-process groups.

    SRP: public API is assign_groups(). Internal stages delegate to standalone
    functions in adjacent modules — no private wrapper methods.
    OCP: constants are sourced from grouping_title_support (single source of truth).
    DIP: AISkillRegistry is injected, not constructed internally.
    """

    _ACCEPTED_AI_CONFIDENCE = {"high", "medium"}
    # OCP fix: import from the single source of truth instead of duplicating.
    _STOPWORDS = STOPWORDS

    def __init__(
        self,
        *,
        process_group_service: ProcessGroupService | None = None,
        ai_transcript_interpreter: AITranscriptInterpreter | None = None,
        ai_skill_registry: AISkillRegistry | None = None,
    ) -> None:
        self.process_group_service = process_group_service or ProcessGroupService()
        self.ai_transcript_interpreter = ai_transcript_interpreter or AITranscriptInterpreter()
        # DIP fix: accept registry from the outside; fall back to default only at boundary.
        self._ai_skill_registry = ai_skill_registry or build_default_ai_skill_registry()
        self._workflow_title_resolution_skill = (
            InterpreterWorkflowTitleResolutionSkill(self.ai_transcript_interpreter)
            if ai_transcript_interpreter is not None
            else None
        )
        self._workflow_group_match_skill = (
            InterpreterWorkflowGroupMatchSkill(self.ai_transcript_interpreter)
            if ai_transcript_interpreter is not None
            else None
        )
        self._process_summary_generation_skill = (
            InterpreterProcessSummarySkill(self.ai_transcript_interpreter)
            if ai_transcript_interpreter is not None
            else None
        )
        self._workflow_capability_tagging_skill = (
            InterpreterWorkflowCapabilityTaggingSkill(self.ai_transcript_interpreter)
            if ai_transcript_interpreter is not None
            else None
        )

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

    def _resolve_group_identity(
        self,
        *,
        transcript: ArtifactModel,
        steps: list[StepRecord],
        notes: list[NoteRecord],
        existing_groups: list[ProcessGroupModel],
        workflow_profile: TranscriptWorkflowProfile,
        previous_workflow_profile: TranscriptWorkflowProfile | None,
        previous_group: ProcessGroupModel | None,
    ) -> GroupResolutionDecision:
        return resolve_group_identity(
            self,
            transcript=transcript,
            steps=steps,
            notes=notes,
            existing_groups=existing_groups,
            workflow_profile=workflow_profile,
            previous_workflow_profile=previous_workflow_profile,
            previous_group=previous_group,
        )

    def _resolve_title_with_ai(
        self,
        *,
        transcript: ArtifactModel,
        steps: list[StepRecord],
        workflow_profile: TranscriptWorkflowProfile,
        fallback_title: str,
    ) -> WorkflowTitleInterpretation:
        return resolve_title_with_ai(
            self,
            transcript=transcript,
            steps=steps,
            workflow_profile=workflow_profile,
            fallback_title=fallback_title,
        )

    def _match_existing_group_with_ai(
        self,
        *,
        transcript: ArtifactModel,
        title_resolution: WorkflowTitleInterpretation,
        workflow_profile: TranscriptWorkflowProfile,
        steps: list[StepRecord],
        notes: list[NoteRecord],
        existing_groups: list[ProcessGroupModel],
        heuristic_match: HeuristicGroupMatchResult,
    ) -> GroupResolutionDecision | None:
        return match_existing_group_with_ai(
            self,
            transcript=transcript,
            title_resolution=title_resolution,
            workflow_profile=workflow_profile,
            steps=steps,
            notes=notes,
            existing_groups=existing_groups,
            heuristic_match=heuristic_match,
        )

    def _resolve_ambiguity_with_ai(
        self,
        *,
        transcript: ArtifactModel,
        inferred_title: str,
        candidate_matches: list[CandidateMatchRecord],
        steps: list[StepRecord],
        notes: list[NoteRecord],
        existing_groups: list[ProcessGroupModel],
    ) -> GroupResolutionDecision | None:
        return resolve_ambiguity(
            self,
            transcript=transcript,
            inferred_title=inferred_title,
            candidate_matches=candidate_matches,
            steps=steps,
            notes=notes,
            existing_groups=existing_groups,
        )

    def _refresh_group_summaries(
        self,
        *,
        process_groups: list[ProcessGroupModel],
        transcript_group_ids: dict[str, str],
        steps_by_transcript: dict[str, list[StepRecord]],
        notes_by_transcript: dict[str, list[NoteRecord]],
        workflow_profiles: dict[str, TranscriptWorkflowProfile],
        document_type: str,
    ) -> None:
        (
            self._process_summary_generation_skill,
            self._workflow_capability_tagging_skill,
        ) = refresh_group_summaries(
            process_groups=process_groups,
            transcript_group_ids=transcript_group_ids,
            steps_by_transcript=steps_by_transcript,
            notes_by_transcript=notes_by_transcript,
            workflow_profiles=workflow_profiles,
            document_type=document_type,
            accepted_ai_confidence=self._ACCEPTED_AI_CONFIDENCE,
            ai_skill_registry=self._ai_skill_registry,
            process_summary_generation_skill=self._process_summary_generation_skill,
            workflow_capability_tagging_skill=self._workflow_capability_tagging_skill,
            logger=logger,
        )

    def _fallback_title(self, *, transcript: ArtifactModel, steps: list[StepRecord], workflow_profile: TranscriptWorkflowProfile) -> str:
        return fallback_title(
            transcript=transcript,
            steps=steps,
            workflow_profile=workflow_profile,
            normalize_text=normalize_text,
            extract_leading_action_verb=extract_leading_action_verb,
        )

    def _match_existing_group(
        self,
        *,
        slug: str,
        title: str,
        steps: list[StepRecord],
        workflow_profile: TranscriptWorkflowProfile,
        existing_groups: list[ProcessGroupModel],
    ) -> HeuristicGroupMatchResult:
        return match_existing_group(
            slug=slug,
            title=title,
            steps=steps,
            workflow_profile=workflow_profile,
            existing_groups=existing_groups,
            normalize_text=normalize_text,
            stopwords=self._STOPWORDS,
            signature_tokens=signature_tokens,
        )

    def _resolve_capability_tags(
        self,
        *,
        process_title: str,
        workflow_summary: dict[str, object],
        workflow_profiles: list[TranscriptWorkflowProfile],
        document_type: str,
    ) -> list[str]:
        (
            capability_tags,
            self._workflow_capability_tagging_skill,
        ) = resolve_capability_tags(
            process_title=process_title,
            workflow_summary=workflow_summary,
            workflow_profiles=workflow_profiles,
            document_type=document_type,
            accepted_ai_confidence=self._ACCEPTED_AI_CONFIDENCE,
            ai_skill_registry=self._ai_skill_registry,
            workflow_capability_tagging_skill=self._workflow_capability_tagging_skill,
            logger=logger,
        )
        return capability_tags

    def _normalize_capability_tags(self, tags: list[str], *, process_title: str) -> list[str]:
        return normalize_capability_tags(tags, process_title=process_title)

    @staticmethod
    def _build_transcript_profiles(
        *,
        evidence_segments: list[EvidenceSegment],
        workflow_boundary_decisions: list[WorkflowBoundaryDecision],
        steps_by_transcript: dict[str, list[StepRecord]],
    ) -> dict[str, TranscriptWorkflowProfile]:
        return build_transcript_profiles(
            evidence_segments=evidence_segments,
            workflow_boundary_decisions=workflow_boundary_decisions,
            steps_by_transcript=steps_by_transcript,
        )
