r"""
Purpose: Assign transcript outputs into logical process groups within a session.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\process_grouping_service.py
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import cast

from app.core.observability import get_logger
from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.process_group import ProcessGroupModel
from app.services.process_group_service import ProcessGroupService
from worker.services.ai_skills.process_summary_generation.schemas import ProcessSummaryGenerationRequest
from worker.services.ai_skills.registry import build_default_ai_skill_registry
from worker.services.ai_skills.workflow_capability_tagging.schemas import WorkflowCapabilityTaggingRequest
from worker.services.ai_skills.workflow_group_match.schemas import WorkflowGroupMatchRequest
from worker.services.ai_skills.workflow_title_resolution.schemas import WorkflowTitleResolutionRequest
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter, WorkflowGroupMatchInterpretation, WorkflowTitleInterpretation
from worker.services.generation_types import NoteRecord, StepRecord
from worker.services.workflow_intelligence import EvidenceSegment, WorkflowBoundaryDecision
from worker.services.workflow_intelligence.grouping_ai_adapters import (
    InterpreterProcessSummarySkill,
    InterpreterWorkflowCapabilityTaggingSkill,
    InterpreterWorkflowGroupMatchSkill,
    InterpreterWorkflowTitleResolutionSkill,
)
from worker.services.workflow_intelligence.grouping_identity_resolution import (
    application_alignment_score,
    build_ai_group_match_decision,
    build_heuristic_group_decision,
    has_explicit_tool_mismatch,
    heuristic_resolution_confidence,
    match_existing_group,
    profile_tokens,
    serialize_existing_groups_for_ai,
    system_alignment_score,
)
from worker.services.workflow_intelligence.grouping_models import (
    CandidateMatchRecord,
    GroupResolutionDecision,
    HeuristicGroupMatchResult,
    ProcessGroupingResult,
    TranscriptWorkflowProfile,
)
from worker.services.workflow_intelligence.grouping_title_resolution import (
    STOPWORDS,
    extract_leading_action_verb,
    fallback_title,
    group_summary_seed,
    normalize_text,
    normalize_workflow_title,
    operation_signature_from_steps,
    preferred_workflow_suffix,
    signature_tokens,
    slugify,
    starts_with_non_business_action,
)

logger = get_logger(__name__)


class ProcessGroupingService:
    """Cluster transcript outputs into same-process vs different-process groups."""

    _ACCEPTED_AI_CONFIDENCE = {"high", "medium"}

    _WORKFLOW_SUFFIX_BY_ACTION = {
        "create": "Creation",
        "submit": "Creation",
        "save": "Creation",
        "update": "Maintenance",
        "edit": "Maintenance",
        "change": "Maintenance",
        "maintain": "Maintenance",
        "review": "Review",
        "approve": "Approval",
        "validate": "Validation",
        "check": "Validation",
        "reconcile": "Reconciliation",
        "post": "Posting",
    }
    _NON_BUSINESS_ACTIONS = {
        "open",
        "go",
        "go to",
        "goto",
        "navigate",
        "launch",
        "login",
        "log in",
        "select",
        "click",
        "enter",
    }
    _STOPWORDS = {
        "a",
        "an",
        "and",
        "the",
        "to",
        "of",
        "for",
        "in",
        "on",
        "with",
        "into",
        "from",
        "then",
        "after",
        "before",
        "click",
        "select",
        "enter",
        "open",
        "go",
        "navigate",
        "screen",
        "field",
        "data",
        "details",
        "form",
        "tab",
        "save",
        "submit",
        "create",
        "creation",
        "process",
    }

    def __init__(
        self,
        *,
        process_group_service: ProcessGroupService | None = None,
        ai_transcript_interpreter: AITranscriptInterpreter | None = None,
    ) -> None:
        self.process_group_service = process_group_service or ProcessGroupService()
        self.ai_transcript_interpreter = ai_transcript_interpreter or AITranscriptInterpreter()
        self._ai_skill_registry = build_default_ai_skill_registry()
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
        process_groups: list[ProcessGroupModel] = []
        transcript_group_ids: dict[str, str] = {}
        assignment_details: list[dict[str, object]] = []
        workflow_profiles = self._build_transcript_profiles(
            evidence_segments=evidence_segments or [],
            workflow_boundary_decisions=workflow_boundary_decisions or [],
            steps_by_transcript=steps_by_transcript,
        )
        sorted_transcripts = self._sort_transcripts(transcript_artifacts)

        for index, transcript in enumerate(sorted_transcripts):
            transcript_steps = steps_by_transcript.get(transcript.id, [])
            transcript_notes = notes_by_transcript.get(transcript.id, [])
            workflow_profile = workflow_profiles.get(
                transcript.id,
                TranscriptWorkflowProfile(
                    transcript_artifact_id=transcript.id,
                    top_actors=[],
                    top_objects=[],
                    top_systems=[],
                    top_applications=[],
                    top_actions=[],
                    top_goals=[],
                    top_rules=[],
                    top_domain_terms=[],
                ),
            )
            previous_transcript = sorted_transcripts[index - 1] if index > 0 else None
            previous_group = process_groups[-1] if process_groups else None
            previous_workflow_profile = workflow_profiles.get(previous_transcript.id) if previous_transcript is not None else None
            resolution = self._resolve_group_identity(
                transcript=transcript,
                steps=transcript_steps,
                notes=transcript_notes,
                existing_groups=process_groups,
                workflow_profile=workflow_profile,
                previous_workflow_profile=previous_workflow_profile,
                previous_group=previous_group,
            )
            matched_group = resolution.matched_group

            if matched_group is None:
                matched_group = self.process_group_service.create_process_group(
                    db,
                    session=session,
                    title=resolution.inferred_title,
                    canonical_slug=resolution.inferred_slug,
                    display_order=len(process_groups) + 1,
                )
                process_groups.append(matched_group)

            matched_group.summary_text = self._group_summary_seed(
                inferred_title=resolution.inferred_title,
                steps=transcript_steps,
                notes=transcript_notes,
                workflow_profile=workflow_profile,
            )
            db.commit()

            transcript_group_ids[transcript.id] = matched_group.id
            assignment_details.append(
                {
                    "transcript_name": transcript.name,
                    "inferred_workflow": resolution.inferred_title,
                    "assigned_group_id": matched_group.id,
                    "assigned_group_title": matched_group.title,
                    "decision": resolution.decision,
                    "decision_confidence": resolution.confidence,
                    "decision_source": resolution.decision_source,
                    "is_ambiguous": resolution.is_ambiguous,
                    "rationale": resolution.rationale,
                    "candidate_matches": resolution.candidate_matches,
                    "supporting_signals": resolution.supporting_signals,
                    "heuristic_decision": resolution.heuristic_decision,
                    "heuristic_confidence": resolution.heuristic_confidence,
                    "ai_decision": resolution.ai_decision,
                    "ai_confidence": resolution.ai_confidence,
                    "conflict_detected": resolution.conflict_detected,
                    "top_goals": workflow_profile.top_goals,
                    "top_objects": workflow_profile.top_objects,
                    "top_systems": workflow_profile.top_systems,
                    "top_applications": workflow_profile.top_applications,
                    "top_actors": workflow_profile.top_actors,
                    "top_rules": workflow_profile.top_rules,
                    "capability_tags": self._parse_capability_tags(getattr(matched_group, "capability_tags_json", "[]")),
                }
            )
            for step in transcript_steps:
                step["process_group_id"] = matched_group.id
            for note in transcript_notes:
                note["process_group_id"] = matched_group.id

        self._refresh_group_summaries(
            process_groups=process_groups,
            transcript_group_ids=transcript_group_ids,
            steps_by_transcript=steps_by_transcript,
            notes_by_transcript=notes_by_transcript,
            workflow_profiles=workflow_profiles,
            document_type=getattr(session, "document_type", "pdd"),
        )
        capability_tags_by_group = {
            group.id: self._parse_capability_tags(getattr(group, "capability_tags_json", "[]"))
            for group in process_groups
        }
        for assignment in assignment_details:
            assigned_group_id = str(assignment.get("assigned_group_id", "") or "")
            if assigned_group_id:
                assignment["capability_tags"] = capability_tags_by_group.get(assigned_group_id, [])

        return ProcessGroupingResult(
            process_groups=process_groups,
            transcript_group_ids=transcript_group_ids,
            assignment_details=assignment_details,
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
        if (
            previous_group is not None
            and previous_workflow_profile is not None
            and previous_workflow_profile.boundary_to_next == "same_workflow"
            and previous_workflow_profile.boundary_to_next_confidence in {"medium", "high"}
        ):
            return GroupResolutionDecision(
                inferred_title=previous_group.title,
                inferred_slug=previous_group.canonical_slug,
                matched_group=previous_group,
                decision="continued_previous_group",
                confidence=previous_workflow_profile.boundary_to_next_confidence or "medium",
                decision_source="heuristic",
                is_ambiguous=False,
                rationale=(
                    "Reused the previous workflow group because adjacent transcript continuity was classified as "
                    f"{previous_workflow_profile.boundary_to_next} with {previous_workflow_profile.boundary_to_next_confidence} confidence."
                ),
                candidate_matches=[{"group_title": previous_group.title, "score": 0.9}],
                supporting_signals=[
                    "adjacent_transcript_continuity",
                    f"boundary:{previous_workflow_profile.boundary_to_next}",
                ],
            )

        title = self._fallback_title(transcript=transcript, steps=steps, workflow_profile=workflow_profile)
        title_resolution = self._resolve_title_with_ai(
            transcript=transcript,
            steps=steps,
            workflow_profile=workflow_profile,
            fallback_title=title,
        )
        title = title_resolution.workflow_title
        slug = title_resolution.canonical_slug
        heuristic_match = self._match_existing_group(
            slug=slug,
            title=title,
            steps=steps,
            workflow_profile=workflow_profile,
            existing_groups=existing_groups,
        )
        ai_group_match = self._match_existing_group_with_ai(
            transcript=transcript,
            title_resolution=title_resolution,
            workflow_profile=workflow_profile,
            steps=steps,
            notes=notes,
            existing_groups=existing_groups,
            heuristic_match=heuristic_match,
        )
        if ai_group_match is not None:
            return ai_group_match
        matched_group = heuristic_match["matched_group"]
        ambiguity = heuristic_match["ambiguity"]
        candidate_matches = heuristic_match["candidate_matches"]
        title_supporting_signals = ["ai_title_resolution"] if title_resolution.rationale else []
        if ambiguity:
            ai_resolution = self._resolve_ambiguity_with_ai(
                transcript=transcript,
                inferred_title=title,
                candidate_matches=candidate_matches,
                steps=steps,
                notes=notes,
                existing_groups=existing_groups,
            )
            if ai_resolution is not None:
                return ai_resolution
        return self._build_heuristic_group_decision(
            inferred_title=title,
            inferred_slug=slug,
            heuristic_match=heuristic_match,
            title_supporting_signals=title_supporting_signals,
        )

    def _resolve_title_with_ai(
        self,
        *,
        transcript: ArtifactModel,
        steps: list[StepRecord],
        workflow_profile: TranscriptWorkflowProfile,
        fallback_title: str,
    ) -> WorkflowTitleInterpretation:
        workflow_summary = self._build_workflow_summary(
            title=fallback_title,
            workflow_profile=workflow_profile,
            steps=steps,
            notes=[],
        )
        if self._workflow_title_resolution_skill is None:
            self._workflow_title_resolution_skill = self._ai_skill_registry.create("workflow_title_resolution")
        logger.info(
            "Delegating workflow title resolution to AI skill.",
            extra={
                "skill_id": "workflow_title_resolution",
                "skill_version": getattr(self._workflow_title_resolution_skill, "version", "unknown"),
                "transcript_name": transcript.name,
            },
        )
        ai_skill_result = self._workflow_title_resolution_skill.run(
            WorkflowTitleResolutionRequest(
                transcript_name=transcript.name,
                workflow_summary=workflow_summary,
            )
        )
        ai_resolution = (
            None
            if ai_skill_result is None
            else WorkflowTitleInterpretation(
                workflow_title=ai_skill_result.workflow_title,
                canonical_slug=ai_skill_result.canonical_slug,
                confidence=ai_skill_result.confidence,
                rationale=ai_skill_result.rationale,
            )
        )
        if ai_resolution is None or ai_resolution.confidence not in self._ACCEPTED_AI_CONFIDENCE:
            return WorkflowTitleInterpretation(
                workflow_title=fallback_title,
                canonical_slug=self._slugify(fallback_title),
                confidence="medium",
                rationale="",
            )
        normalized_title = self._normalize_workflow_title(
            base_title=ai_resolution.workflow_title.strip() or fallback_title,
            steps=steps,
            workflow_profile=workflow_profile,
        )
        return WorkflowTitleInterpretation(
            workflow_title=normalized_title,
            canonical_slug=self._slugify(ai_resolution.canonical_slug or normalized_title or fallback_title),
            confidence=ai_resolution.confidence,
            rationale=ai_resolution.rationale,
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
        if not existing_groups:
            return None

        workflow_summary = self._build_workflow_summary(
            title=title_resolution.workflow_title,
            workflow_profile=workflow_profile,
            steps=steps,
            notes=notes,
        )
        serialized_existing_groups = self._serialize_existing_groups_for_ai(
            existing_groups=existing_groups,
            heuristic_match=heuristic_match,
        )
        if self._workflow_group_match_skill is None:
            self._workflow_group_match_skill = self._ai_skill_registry.create("workflow_group_match")
        logger.info(
            "Delegating workflow group match to AI skill.",
            extra={
                "skill_id": "workflow_group_match",
                "skill_version": getattr(self._workflow_group_match_skill, "version", "unknown"),
                "transcript_name": transcript.name,
            },
        )
        ai_skill_result = self._workflow_group_match_skill.run(
            WorkflowGroupMatchRequest(
                transcript_name=transcript.name,
                workflow_summary=workflow_summary,
                existing_groups=serialized_existing_groups,
            )
        )
        if not ai_skill_result.recommended_title and ai_skill_result.matched_existing_title is None:
            return None
        ai_match = WorkflowGroupMatchInterpretation(
            matched_existing_title=ai_skill_result.matched_existing_title,
            recommended_title=ai_skill_result.recommended_title,
            recommended_slug=ai_skill_result.recommended_slug,
            confidence=ai_skill_result.confidence,
            rationale=ai_skill_result.rationale,
        )

        heuristic_group = heuristic_match["matched_group"]
        heuristic_title = heuristic_group.title if heuristic_group is not None else None
        heuristic_confidence = self._heuristic_resolution_confidence(heuristic_match)
        heuristic_decision = "matched_existing_group" if heuristic_title is not None else "created_new_group"
        ai_decision = "matched_existing_group" if ai_match.matched_existing_title else "created_new_group"
        conflict_detected = heuristic_title != ai_match.matched_existing_title
        if not conflict_detected:
            return self._build_ai_group_match_decision(
                ai_match=ai_match,
                fallback_title=title_resolution.workflow_title,
                existing_groups=existing_groups,
                decision_source="ai",
                heuristic_decision=heuristic_decision,
                heuristic_confidence=heuristic_confidence,
                ai_decision=ai_decision,
                ai_confidence=ai_match.confidence,
                conflict_detected=False,
            )

        if ai_match.confidence == "high" and heuristic_confidence != "high":
            return self._build_ai_group_match_decision(
                ai_match=ai_match,
                fallback_title=title_resolution.workflow_title,
                existing_groups=existing_groups,
                decision_source="ai_conflict_override",
                heuristic_decision=heuristic_decision,
                heuristic_confidence=heuristic_confidence,
                ai_decision=ai_decision,
                ai_confidence=ai_match.confidence,
                conflict_detected=True,
                supporting_signals=["ai_group_matcher", "grouping_conflict_detected", "ai_conflict_override"],
                rationale_prefix=(
                    f"AI grouping recommendation conflicted with the heuristic {heuristic_decision.replace('_', ' ')} "
                    f"decision, so the AI recommendation was used because it had high confidence while the heuristic confidence was {heuristic_confidence}."
                ),
            )

        if heuristic_confidence == "high" and ai_match.confidence != "high":
            return self._build_heuristic_group_decision(
                inferred_title=title_resolution.workflow_title,
                inferred_slug=title_resolution.canonical_slug,
                heuristic_match=heuristic_match,
                title_supporting_signals=["ai_title_resolution"] if title_resolution.rationale else [],
                decision_source="heuristic_fallback",
                rationale_override=(
                    f"AI suggested {'existing workflow ' + ai_match.matched_existing_title if ai_match.matched_existing_title else 'creating a new workflow'}, "
                    f"but the heuristic {heuristic_decision.replace('_', ' ')} decision remained stronger, so the heuristic result was kept."
                ),
                heuristic_decision=heuristic_decision,
                heuristic_confidence=heuristic_confidence,
                ai_decision=ai_decision,
                ai_confidence=ai_match.confidence,
                conflict_detected=True,
                extra_supporting_signals=["grouping_conflict_detected", "heuristic_fallback"],
            )

        return self._build_heuristic_group_decision(
            inferred_title=title_resolution.workflow_title,
            inferred_slug=title_resolution.canonical_slug,
            heuristic_match=heuristic_match,
            title_supporting_signals=["ai_title_resolution"] if title_resolution.rationale else [],
            decision_source="conflict_unresolved",
            force_ambiguous=True,
            rationale_override=(
                f"AI and heuristic grouping both produced credible but conflicting outcomes for '{title_resolution.workflow_title}', "
                "so the system kept the conservative heuristic assignment and marked it ambiguous for later review."
            ),
            heuristic_decision=heuristic_decision,
            heuristic_confidence=heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_match.confidence,
            conflict_detected=True,
            extra_supporting_signals=["grouping_conflict_detected", "conflict_unresolved"],
        )

    def _build_ai_group_match_decision(
        self,
        *,
        ai_match: WorkflowGroupMatchInterpretation,
        fallback_title: str,
        existing_groups: list[ProcessGroupModel],
        decision_source: str,
        heuristic_decision: str | None,
        heuristic_confidence: str | None,
        ai_decision: str,
        ai_confidence: str,
        conflict_detected: bool,
        supporting_signals: list[str] | None = None,
        rationale_prefix: str = "",
    ) -> GroupResolutionDecision:
        return build_ai_group_match_decision(
            ai_match=ai_match,
            fallback_title=fallback_title,
            existing_groups=existing_groups,
            decision_source=decision_source,
            heuristic_decision=heuristic_decision,
            heuristic_confidence=heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_confidence,
            conflict_detected=conflict_detected,
            supporting_signals=supporting_signals,
            rationale_prefix=rationale_prefix,
        )

    def _build_heuristic_group_decision(
        self,
        *,
        inferred_title: str,
        inferred_slug: str,
        heuristic_match: HeuristicGroupMatchResult,
        title_supporting_signals: list[str],
        decision_source: str = "heuristic",
        force_ambiguous: bool = False,
        rationale_override: str | None = None,
        heuristic_decision: str | None = None,
        heuristic_confidence: str | None = None,
        ai_decision: str | None = None,
        ai_confidence: str | None = None,
        conflict_detected: bool = False,
        extra_supporting_signals: list[str] | None = None,
    ) -> GroupResolutionDecision:
        return build_heuristic_group_decision(
            inferred_title=inferred_title,
            inferred_slug=inferred_slug,
            heuristic_match=heuristic_match,
            title_supporting_signals=title_supporting_signals,
            decision_source=decision_source,
            force_ambiguous=force_ambiguous,
            rationale_override=rationale_override,
            heuristic_decision=heuristic_decision,
            heuristic_confidence=heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_confidence,
            conflict_detected=conflict_detected,
            extra_supporting_signals=extra_supporting_signals,
        )

    def _heuristic_resolution_confidence(self, heuristic_match: HeuristicGroupMatchResult) -> str:
        return heuristic_resolution_confidence(heuristic_match)

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
        ai_resolution = self.ai_transcript_interpreter.resolve_ambiguous_process_group(
            transcript_name=transcript.name,
            inferred_title=inferred_title,
            candidate_matches=candidate_matches,
            steps=steps,
            notes=notes,
        )
        if ai_resolution is None:
            return None

        matched_group = next(
            (group for group in existing_groups if group.title == ai_resolution.matched_existing_title),
            None,
        )
        resolved_title = ai_resolution.recommended_title.strip() or inferred_title
        resolved_slug = self._slugify(ai_resolution.recommended_slug or resolved_title)
        if matched_group is not None:
            return GroupResolutionDecision(
                inferred_title=resolved_title,
                inferred_slug=resolved_slug,
                matched_group=matched_group,
                decision="ai_resolved_ambiguous_match",
                confidence=ai_resolution.confidence,
                decision_source="ai_tiebreak",
                is_ambiguous=False,
                rationale=ai_resolution.rationale or f"AI resolved the ambiguity in favor of existing workflow '{matched_group.title}'.",
                candidate_matches=candidate_matches,
                supporting_signals=["ai_ambiguity_resolution"],
            )
        return GroupResolutionDecision(
            inferred_title=resolved_title,
            inferred_slug=resolved_slug,
            matched_group=None,
            decision="ai_resolved_ambiguous_new_group",
            confidence=ai_resolution.confidence,
            decision_source="ai_tiebreak",
            is_ambiguous=False,
            rationale=ai_resolution.rationale or f"AI resolved the ambiguity in favor of creating a new workflow '{resolved_title}'.",
            candidate_matches=candidate_matches,
            supporting_signals=["ai_ambiguity_resolution"],
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
        )

    def _system_alignment_score(self, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str]) -> float:
        return system_alignment_score(workflow_profile, group_tokens)

    def _application_alignment_score(self, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str]) -> float:
        return application_alignment_score(workflow_profile, group_tokens)

    def _has_explicit_tool_mismatch(self, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str]) -> bool:
        return has_explicit_tool_mismatch(workflow_profile, group_tokens)

    def _fallback_title(self, *, transcript: ArtifactModel, steps: list[StepRecord], workflow_profile: TranscriptWorkflowProfile) -> str:
        return fallback_title(transcript=transcript, steps=steps, workflow_profile=workflow_profile)

    def _normalize_workflow_title(
        self,
        *,
        base_title: str,
        steps: list[StepRecord],
        workflow_profile: TranscriptWorkflowProfile,
    ) -> str:
        return normalize_workflow_title(base_title=base_title, steps=steps, workflow_profile=workflow_profile)

    def _preferred_workflow_suffix(self, *, steps: list[StepRecord], workflow_profile: TranscriptWorkflowProfile) -> str:
        return preferred_workflow_suffix(steps=steps, workflow_profile=workflow_profile)

    def _starts_with_non_business_action(self, title: str) -> bool:
        return starts_with_non_business_action(title)

    @staticmethod
    def _extract_leading_action_verb(action_text: str) -> str:
        return extract_leading_action_verb(action_text)

    def _group_summary_seed(
        self,
        *,
        inferred_title: str,
        steps: list[StepRecord],
        notes: list[NoteRecord],
        workflow_profile: TranscriptWorkflowProfile,
    ) -> str:
        return group_summary_seed(
            inferred_title=inferred_title,
            steps=steps,
            notes=notes,
            workflow_profile=workflow_profile,
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
        if not process_groups:
            return

        transcript_ids_by_group: dict[str, list[str]] = defaultdict(list)
        for transcript_id, group_id in transcript_group_ids.items():
            transcript_ids_by_group[group_id].append(transcript_id)

        for process_group in process_groups:
            transcript_ids = transcript_ids_by_group.get(process_group.id, [])
            group_steps = [
                cast(StepRecord, dict(step))
                for transcript_id in transcript_ids
                for step in steps_by_transcript.get(transcript_id, [])
            ]
            group_notes = [
                cast(NoteRecord, dict(note))
                for transcript_id in transcript_ids
                for note in notes_by_transcript.get(transcript_id, [])
            ]
            group_profiles = [
                workflow_profiles[transcript_id]
                for transcript_id in transcript_ids
                if transcript_id in workflow_profiles
            ]
            fallback_summary = self._build_process_summary_fallback(
                process_title=process_group.title,
                workflow_profiles=group_profiles,
                steps=group_steps,
                notes=group_notes,
            )
            workflow_summary = self._build_group_workflow_summary(
                title=process_group.title,
                workflow_profiles=group_profiles,
                steps=group_steps,
                notes=group_notes,
            )
            if self._process_summary_generation_skill is None:
                self._process_summary_generation_skill = self._ai_skill_registry.create("process_summary_generation")
            logger.info(
                "Delegating process summary generation to AI skill.",
                extra={
                    "skill_id": "process_summary_generation",
                    "skill_version": getattr(self._process_summary_generation_skill, "version", "unknown"),
                    "process_title": process_group.title,
                },
            )
            ai_summary = self._process_summary_generation_skill.run(
                ProcessSummaryGenerationRequest(
                    process_title=process_group.title,
                    workflow_summary=workflow_summary,
                    steps=group_steps[:12],
                    notes=group_notes[:6],
                    document_type=document_type,
                )
            )
            if ai_summary is not None and ai_summary.confidence in self._ACCEPTED_AI_CONFIDENCE:
                process_group.summary_text = ai_summary.summary_text
            else:
                process_group.summary_text = fallback_summary
            process_group.capability_tags_json = json.dumps(
                self._resolve_capability_tags(
                    process_title=process_group.title,
                    workflow_summary=workflow_summary,
                    workflow_profiles=group_profiles,
                    document_type=document_type,
                )
            )

    def _build_group_workflow_summary(
        self,
        *,
        title: str,
        workflow_profiles: list[TranscriptWorkflowProfile],
        steps: list[StepRecord],
        notes: list[NoteRecord],
    ) -> dict[str, object]:
        actors = self._merge_profile_lists(workflow_profiles, "top_actors", limit=4)
        objects = self._merge_profile_lists(workflow_profiles, "top_objects", limit=4)
        systems = self._merge_profile_lists(workflow_profiles, "top_systems", limit=4)
        actions = self._merge_profile_lists(workflow_profiles, "top_actions", limit=4)
        goals = self._merge_profile_lists(workflow_profiles, "top_goals", limit=4)
        rules = self._merge_profile_lists(workflow_profiles, "top_rules", limit=4)
        return {
            "suggested_title": title,
            "top_actors": actors,
            "top_objects": objects,
            "top_systems": systems,
            "top_applications": self._merge_profile_lists(workflow_profiles, "top_applications", limit=4),
            "top_actions": actions,
            "top_goals": goals,
            "top_rules": rules,
            "top_domain_terms": self._merge_profile_lists(workflow_profiles, "top_domain_terms", limit=6),
            "operational_signature": self._operation_signature_from_steps(steps),
            "step_samples": [
                {
                    "action_text": str(step.get("action_text", "") or ""),
                    "supporting_transcript_text": str(step.get("supporting_transcript_text", "") or ""),
                }
                for step in steps[:10]
            ],
            "note_samples": [str(note.get("text", "") or "") for note in notes[:6]],
        }

    def _build_process_summary_fallback(
        self,
        *,
        process_title: str,
        workflow_profiles: list[TranscriptWorkflowProfile],
        steps: list[StepRecord],
        notes: list[NoteRecord],
    ) -> str:
        top_goals = self._merge_profile_lists(workflow_profiles, "top_goals", limit=2)
        top_objects = self._merge_profile_lists(workflow_profiles, "top_objects", limit=3)
        top_systems = self._merge_profile_lists(workflow_profiles, "top_systems", limit=2)
        top_rules = self._merge_profile_lists(workflow_profiles, "top_rules", limit=2)
        summary_parts = [f"{process_title} covers the workflow"]
        if top_goals:
            summary_parts.append(f"focused on {', '.join(top_goals)}")
        elif top_objects:
            summary_parts.append(f"focused on {', '.join(top_objects)}")
        if top_systems:
            summary_parts.append(f"using {', '.join(top_systems)}")
        sentence_one = " ".join(summary_parts).strip().rstrip(".") + "."

        key_actions = [
            str(step.get("action_text", "") or "").strip()
            for step in steps[:3]
            if str(step.get("action_text", "") or "").strip()
        ]
        sentence_two = ""
        if key_actions:
            sentence_two = f"Key business actions include {', '.join(key_actions)}."

        sentence_three = ""
        if top_rules:
            sentence_three = f"Important workflow considerations include {', '.join(top_rules)}."
        elif notes:
            note_text = str(notes[0].get("text", "") or "").strip()
            if note_text:
                sentence_three = f"Supporting process context includes {note_text}."

        return " ".join(part for part in (sentence_one, sentence_two, sentence_three) if part).strip()

    def _resolve_capability_tags(
        self,
        *,
        process_title: str,
        workflow_summary: dict[str, object],
        workflow_profiles: list[TranscriptWorkflowProfile],
        document_type: str,
    ) -> list[str]:
        if self._workflow_capability_tagging_skill is None:
            self._workflow_capability_tagging_skill = self._ai_skill_registry.create("workflow_capability_tagging")
        logger.info(
            "Delegating workflow capability tagging to AI skill.",
            extra={
                "skill_id": "workflow_capability_tagging",
                "skill_version": getattr(self._workflow_capability_tagging_skill, "version", "unknown"),
                "process_title": process_title,
            },
        )
        ai_capabilities = self._workflow_capability_tagging_skill.run(
            WorkflowCapabilityTaggingRequest(
                process_title=process_title,
                workflow_summary=workflow_summary,
                document_type=document_type,
            )
        )
        if ai_capabilities is not None and ai_capabilities.confidence in self._ACCEPTED_AI_CONFIDENCE and ai_capabilities.capability_tags:
            normalized_tags = self._normalize_capability_tags(
                ai_capabilities.capability_tags,
                process_title=process_title,
            )
            if normalized_tags:
                return normalized_tags
        fallback_tags = self._fallback_capability_tags(workflow_profiles=workflow_profiles)
        return fallback_tags if fallback_tags else [process_title]

    def _fallback_capability_tags(self, *, workflow_profiles: list[TranscriptWorkflowProfile]) -> list[str]:
        ordered = self._merge_profile_lists(workflow_profiles, "top_domain_terms", limit=3)
        fallback = [self._to_capability_label(value) for value in ordered if value]
        return self._normalize_capability_tags(fallback, process_title="")

    @staticmethod
    def _merge_profile_lists(
        workflow_profiles: list[TranscriptWorkflowProfile],
        attribute_name: str,
        *,
        limit: int,
    ) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for profile in workflow_profiles:
            for value in getattr(profile, attribute_name):
                if value in seen:
                    continue
                seen.add(value)
                ordered.append(value)
                if len(ordered) >= limit:
                    return ordered
        return ordered

    @staticmethod
    def _to_capability_label(value: str) -> str:
        return " ".join(part.capitalize() for part in value.split())

    def _normalize_capability_tags(self, tags: list[str], *, process_title: str) -> list[str]:
        normalized_process_title = self._normalize_text(process_title)
        normalized_tags: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            cleaned = re.sub(r"\s+", " ", str(tag or "").strip())
            if not cleaned:
                continue
            normalized_key = self._normalize_text(cleaned)
            if not normalized_key or normalized_key == normalized_process_title or normalized_key in seen:
                continue
            seen.add(normalized_key)
            normalized_tags.append(cleaned)
            if len(normalized_tags) >= 3:
                break
        return normalized_tags

    @staticmethod
    def _parse_capability_tags(value: str) -> list[str]:
        try:
            parsed = json.loads(value or "[]")
        except json.JSONDecodeError:
            return []
        return [item for item in parsed if isinstance(item, str)]

    def _build_workflow_summary(
        self,
        *,
        title: str,
        workflow_profile: TranscriptWorkflowProfile,
        steps: list[StepRecord],
        notes: list[NoteRecord],
    ) -> dict[str, object]:
        return {
            "suggested_title": title,
            "top_actors": workflow_profile.top_actors,
            "top_objects": workflow_profile.top_objects,
            "top_systems": workflow_profile.top_systems,
            "top_applications": workflow_profile.top_applications,
            "top_actions": workflow_profile.top_actions,
            "top_goals": workflow_profile.top_goals,
            "top_rules": workflow_profile.top_rules,
            "top_domain_terms": workflow_profile.top_domain_terms,
            "operational_signature": self._operation_signature_from_steps(steps),
            "step_samples": [
                {
                    "action_text": str(step.get("action_text", "") or ""),
                    "supporting_transcript_text": str(step.get("supporting_transcript_text", "") or ""),
                }
                for step in steps[:8]
            ],
            "note_samples": [str(note.get("text", "") or "") for note in notes[:4]],
        }

    def _signature_tokens(self, steps: list[StepRecord]) -> set[str]:
        return signature_tokens(steps)

    def _operation_signature_from_steps(self, steps: list[StepRecord]) -> list[str]:
        return operation_signature_from_steps(steps)

    def _serialize_existing_groups_for_ai(
        self,
        *,
        existing_groups: list[ProcessGroupModel],
        heuristic_match: HeuristicGroupMatchResult,
    ) -> list[dict[str, object]]:
        return serialize_existing_groups_for_ai(
            existing_groups=existing_groups,
            heuristic_match=heuristic_match,
            parse_capability_tags=self._parse_capability_tags,
        )

    @staticmethod
    def _sort_transcripts(transcript_artifacts: list[ArtifactModel]) -> list[ArtifactModel]:
        return sorted(
            transcript_artifacts,
            key=lambda artifact: (
                meeting.order_index
                if (meeting := getattr(artifact, "meeting", None)) is not None and meeting.order_index is not None
                else 1_000_000,
                meeting_date.isoformat()
                if (meeting := getattr(artifact, "meeting", None)) is not None
                and (meeting_date := getattr(meeting, "meeting_date", None)) is not None
                else "",
                uploaded_at.isoformat()
                if (meeting := getattr(artifact, "meeting", None)) is not None
                and (uploaded_at := getattr(meeting, "uploaded_at", None)) is not None
                else "",
                artifact.id,
            ),
        )

    @staticmethod
    def _normalize_text(value: str) -> str:
        return normalize_text(value)

    @staticmethod
    def _slugify(value: str) -> str:
        return slugify(value)

    @staticmethod
    def _build_transcript_profiles(
        *,
        evidence_segments: list[EvidenceSegment],
        workflow_boundary_decisions: list[WorkflowBoundaryDecision],
        steps_by_transcript: dict[str, list[StepRecord]],
    ) -> dict[str, TranscriptWorkflowProfile]:
        segments_by_id = {segment.id: segment for segment in evidence_segments}
        object_counts: dict[str, Counter[str]] = defaultdict(Counter)
        actor_counts: dict[str, Counter[str]] = defaultdict(Counter)
        system_counts: dict[str, Counter[str]] = defaultdict(Counter)
        application_counts: dict[str, Counter[str]] = defaultdict(Counter)
        action_counts: dict[str, Counter[str]] = defaultdict(Counter)
        goal_counts: dict[str, Counter[str]] = defaultdict(Counter)
        rule_counts: dict[str, Counter[str]] = defaultdict(Counter)
        domain_term_counts: dict[str, Counter[str]] = defaultdict(Counter)

        for segment in evidence_segments:
            enrichment = segment.enrichment
            if enrichment is None:
                continue
            transcript_id = segment.transcript_artifact_id
            if enrichment.actor:
                actor_counts[transcript_id][enrichment.actor] += 1
            if enrichment.business_object:
                object_counts[transcript_id][enrichment.business_object] += 1
            if enrichment.system_name:
                system_counts[transcript_id][enrichment.system_name] += 1
            if enrichment.action_verb:
                action_counts[transcript_id][enrichment.action_verb] += 1
            if enrichment.workflow_goal:
                goal_counts[transcript_id][enrichment.workflow_goal] += 1
            for rule_hint in enrichment.rule_hints:
                rule_counts[transcript_id][rule_hint] += 1
            for domain_term in enrichment.domain_terms:
                domain_term_counts[transcript_id][domain_term] += 1
        for transcript_id, steps in steps_by_transcript.items():
            for step in steps:
                application_name = str(step.get("application_name", "") or "").strip()
                if application_name:
                    application_counts[transcript_id][application_name] += 1
                action_text = str(step.get("action_text", "") or "").strip()
                leading_action = extract_leading_action_verb(action_text)
                if leading_action:
                    action_counts[transcript_id][leading_action] += 1

        boundary_map: dict[str, tuple[str, str]] = {}
        for decision in workflow_boundary_decisions:
            left_segment = segments_by_id.get(decision.left_segment_id)
            right_segment = segments_by_id.get(decision.right_segment_id)
            if left_segment is None or right_segment is None:
                continue
            if left_segment.transcript_artifact_id == right_segment.transcript_artifact_id:
                continue
            boundary_map[left_segment.transcript_artifact_id] = (decision.decision, decision.confidence)

        transcript_ids = {segment.transcript_artifact_id for segment in evidence_segments} | set(steps_by_transcript)
        profiles: dict[str, TranscriptWorkflowProfile] = {}
        for transcript_id in transcript_ids:
            boundary = boundary_map.get(transcript_id)
            profiles[transcript_id] = TranscriptWorkflowProfile(
                transcript_artifact_id=transcript_id,
                top_actors=[value for value, _ in actor_counts[transcript_id].most_common(3)],
                top_objects=[value for value, _ in object_counts[transcript_id].most_common(3)],
                top_systems=[value for value, _ in system_counts[transcript_id].most_common(3)],
                top_applications=[value for value, _ in application_counts[transcript_id].most_common(3)],
                top_actions=[value for value, _ in action_counts[transcript_id].most_common(3)],
                top_goals=[value for value, _ in goal_counts[transcript_id].most_common(3)],
                top_rules=[value for value, _ in rule_counts[transcript_id].most_common(2)],
                top_domain_terms=[value for value, _ in domain_term_counts[transcript_id].most_common(4)],
                boundary_to_next=boundary[0] if boundary else None,
                boundary_to_next_confidence=boundary[1] if boundary else None,
            )
        return profiles

    def _profile_tokens(self, profile: TranscriptWorkflowProfile) -> set[str]:
        return profile_tokens(profile)
