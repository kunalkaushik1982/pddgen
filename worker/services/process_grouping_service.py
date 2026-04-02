r"""
Purpose: Assign transcript outputs into logical process groups within a session.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\process_grouping_service.py
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import TypedDict

from app.core.observability import get_logger
from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.process_group import ProcessGroupModel
from app.services.process_group_service import ProcessGroupService
from worker.services.ai_transcript_interpreter import (
    AITranscriptInterpreter,
    WorkflowCapabilityInterpretation,
    WorkflowGroupMatchInterpretation,
    WorkflowTitleInterpretation,
)
from worker.services.workflow_intelligence import EvidenceSegment, WorkflowBoundaryDecision

logger = get_logger(__name__)


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

    def assign_groups(
        self,
        *,
        db,
        session: DraftSessionModel,
        transcript_artifacts: list[ArtifactModel],
        steps_by_transcript: dict[str, list[dict]],
        notes_by_transcript: dict[str, list[dict]],
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
        steps: list[dict],
        notes: list[dict],
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
        steps: list[dict],
        workflow_profile: TranscriptWorkflowProfile,
        fallback_title: str,
    ) -> WorkflowTitleInterpretation:
        workflow_summary = self._build_workflow_summary(
            title=fallback_title,
            workflow_profile=workflow_profile,
            steps=steps,
            notes=[],
        )
        ai_resolution = self.ai_transcript_interpreter.resolve_workflow_title(
            transcript_name=transcript.name,
            workflow_summary=workflow_summary,
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
        steps: list[dict],
        notes: list[dict],
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
        ai_match = self.ai_transcript_interpreter.match_existing_workflow_group(
            transcript_name=transcript.name,
            workflow_summary=workflow_summary,
            existing_groups=self._serialize_existing_groups_for_ai(
                existing_groups=existing_groups,
                heuristic_match=heuristic_match,
            ),
        )
        if ai_match is None:
            return None

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
        matched_group = next(
            (group for group in existing_groups if group.title == ai_match.matched_existing_title),
            None,
        )
        resolved_title = ai_match.recommended_title.strip() or fallback_title
        resolved_slug = self._slugify(ai_match.recommended_slug or resolved_title)
        rationale = ai_match.rationale or (
            f"AI matched this transcript to existing workflow '{matched_group.title}'."
            if matched_group is not None
            else f"AI determined this transcript should create workflow '{resolved_title}'."
        )
        if rationale_prefix:
            rationale = f"{rationale_prefix} {rationale}".strip()
        if matched_group is not None:
            return GroupResolutionDecision(
                inferred_title=resolved_title,
                inferred_slug=resolved_slug,
                matched_group=matched_group,
                decision="ai_matched_existing_group",
                confidence=ai_match.confidence,
                decision_source=decision_source,
                is_ambiguous=False,
                rationale=rationale,
                candidate_matches=[{"group_title": matched_group.title, "score": ai_match.confidence}],
                supporting_signals=supporting_signals or ["ai_group_matcher"],
                heuristic_decision=heuristic_decision,
                heuristic_confidence=heuristic_confidence,
                ai_decision=ai_decision,
                ai_confidence=ai_confidence,
                conflict_detected=conflict_detected,
            )
        return GroupResolutionDecision(
            inferred_title=resolved_title,
            inferred_slug=resolved_slug,
            matched_group=None,
            decision="ai_created_new_group",
            confidence=ai_match.confidence,
            decision_source=decision_source,
            is_ambiguous=False,
            rationale=rationale,
            candidate_matches=[],
            supporting_signals=supporting_signals or ["ai_group_matcher"],
            heuristic_decision=heuristic_decision,
            heuristic_confidence=heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_confidence,
            conflict_detected=conflict_detected,
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
        matched_group = heuristic_match["matched_group"]
        ambiguity = bool(heuristic_match["ambiguity"]) or force_ambiguous
        candidate_matches = list(heuristic_match["candidate_matches"])
        supporting_signals = [
            *title_supporting_signals,
            *list(heuristic_match["supporting_signals"]),
            *(extra_supporting_signals or []),
        ]
        resolved_heuristic_decision = heuristic_decision or ("matched_existing_group" if matched_group is not None else "created_new_group")
        resolved_heuristic_confidence = heuristic_confidence or self._heuristic_resolution_confidence(heuristic_match)
        if matched_group is not None:
            return GroupResolutionDecision(
                inferred_title=inferred_title,
                inferred_slug=inferred_slug,
                matched_group=matched_group,
                decision="matched_existing_group" if not ambiguity else "ambiguously_matched_existing_group",
                confidence=resolved_heuristic_confidence,
                decision_source=decision_source,
                is_ambiguous=ambiguity,
                rationale=(
                    rationale_override
                    or (
                        f"Matched to existing workflow '{matched_group.title}' using title and profile overlap."
                        if not ambiguity
                        else f"Matched to existing workflow '{matched_group.title}', but another plausible workflow also scored closely."
                    )
                ),
                candidate_matches=candidate_matches,
                supporting_signals=supporting_signals,
                heuristic_decision=resolved_heuristic_decision,
                heuristic_confidence=resolved_heuristic_confidence,
                ai_decision=ai_decision,
                ai_confidence=ai_confidence,
                conflict_detected=conflict_detected,
            )
        return GroupResolutionDecision(
            inferred_title=inferred_title,
            inferred_slug=inferred_slug,
            matched_group=None,
            decision="created_new_group" if not ambiguity else "ambiguously_created_new_group",
            confidence="medium" if ambiguity else resolved_heuristic_confidence,
            decision_source=decision_source,
            is_ambiguous=ambiguity,
            rationale=(
                rationale_override
                or (
                    f"No strong existing workflow match was found for inferred workflow '{inferred_title}'."
                    if not ambiguity
                    else f"No confident workflow match was found for inferred workflow '{inferred_title}', so a new group was created conservatively."
                )
            ),
            candidate_matches=candidate_matches,
            supporting_signals=supporting_signals,
            heuristic_decision=resolved_heuristic_decision,
            heuristic_confidence=resolved_heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_confidence,
            conflict_detected=conflict_detected,
        )

    def _heuristic_resolution_confidence(self, heuristic_match: HeuristicGroupMatchResult) -> str:
        best_score = float(heuristic_match["best_score"])
        matched_group = heuristic_match["matched_group"]
        ambiguity = bool(heuristic_match["ambiguity"])
        if ambiguity:
            return "medium"
        if matched_group is not None:
            return "high" if best_score >= 0.9 else "medium"
        return "high" if best_score < 0.55 else "medium"

    def _resolve_ambiguity_with_ai(
        self,
        *,
        transcript: ArtifactModel,
        inferred_title: str,
        candidate_matches: list[CandidateMatchRecord],
        steps: list[dict],
        notes: list[dict],
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
        steps: list[dict],
        workflow_profile: TranscriptWorkflowProfile,
        existing_groups: list[ProcessGroupModel],
    ) -> HeuristicGroupMatchResult:
        for group in existing_groups:
            if slug and group.canonical_slug == slug:
                return {
                    "matched_group": group,
                    "best_score": 1.0,
                    "ambiguity": False,
                    "candidate_matches": [{"group_title": group.title, "score": 1.0}],
                    "supporting_signals": ["canonical_slug_match"],
                }

        normalized_title = self._normalize_text(title)
        candidate_signature = self._signature_tokens(steps)
        profile_tokens = self._profile_tokens(workflow_profile)
        best_group: ProcessGroupModel | None = None
        best_score = 0.0
        second_best_score = 0.0
        candidate_scores: list[CandidateMatchRecord] = []
        for group in existing_groups:
            title_ratio = SequenceMatcher(None, normalized_title, self._normalize_text(group.title)).ratio()
            signature_overlap = 0.0
            system_alignment = 0.0
            application_alignment = 0.0
            group_tokens: set[str] = set()
            if getattr(group, "summary_text", ""):
                group_tokens = {token for token in self._normalize_text(group.summary_text).split() if token and token not in self._STOPWORDS}
                signature_overlap = len(candidate_signature & group_tokens) / max(len(candidate_signature | group_tokens), 1)
                profile_overlap = len(profile_tokens & group_tokens) / max(len(profile_tokens | group_tokens), 1) if profile_tokens else 0.0
                system_alignment = self._system_alignment_score(workflow_profile, group_tokens)
                application_alignment = self._application_alignment_score(workflow_profile, group_tokens)
            else:
                profile_overlap = 0.0
            score = (
                (title_ratio * 0.35)
                + (signature_overlap * 0.18)
                + (profile_overlap * 0.12)
                + (system_alignment * 0.15)
                + (application_alignment * 0.2)
            )
            if self._has_explicit_tool_mismatch(workflow_profile, group_tokens):
                score -= 0.25
            candidate_scores.append(
                {
                    "group_title": group.title,
                    "score": round(score, 3),
                    "title_ratio": round(title_ratio, 3),
                    "signature_overlap": round(signature_overlap, 3),
                    "profile_overlap": round(profile_overlap, 3),
                    "system_alignment": round(system_alignment, 3),
                    "application_alignment": round(application_alignment, 3),
                }
            )
            if score > best_score:
                second_best_score = best_score
                best_score = score
                best_group = group
            elif score > second_best_score:
                second_best_score = score

        candidate_scores.sort(key=lambda item: float(item.get("score", 0.0) or 0.0), reverse=True)
        ambiguity = (
            best_score >= 0.72
            and second_best_score >= 0.7
            and abs(best_score - second_best_score) <= 0.15
        )
        supporting_signals = []
        if best_score >= 0.82:
            supporting_signals.append("strong_existing_group_match")
        elif best_score >= 0.72:
            supporting_signals.append("moderate_existing_group_match")
        if ambiguity:
            supporting_signals.append("competing_group_candidates")

        return {
            "matched_group": best_group if best_score >= 0.86 else None,
            "best_score": best_score,
            "ambiguity": ambiguity,
            "candidate_matches": candidate_scores[:3],
            "supporting_signals": supporting_signals,
        }

    def _system_alignment_score(self, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str]) -> float:
        if not workflow_profile.top_systems:
            return 0.0
        normalized_systems = {self._normalize_text(value) for value in workflow_profile.top_systems if value}
        if not normalized_systems:
            return 0.0
        if any(system in " ".join(group_tokens) for system in normalized_systems):
            return 1.0
        return -0.5

    def _application_alignment_score(self, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str]) -> float:
        if not workflow_profile.top_applications:
            return 0.0
        normalized_applications = {self._normalize_text(value) for value in workflow_profile.top_applications if value}
        if not normalized_applications:
            return 0.0
        if any(application in " ".join(group_tokens) for application in normalized_applications):
            return 1.0
        return -0.75

    def _has_explicit_tool_mismatch(self, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str]) -> bool:
        tool_markers = [self._normalize_text(value) for value in [*workflow_profile.top_systems, *workflow_profile.top_applications] if value]
        if len(tool_markers) == 0:
            return False
        normalized_group_text = " ".join(group_tokens)
        return all(marker not in normalized_group_text for marker in tool_markers)

    def _fallback_title(self, *, transcript: ArtifactModel, steps: list[dict], workflow_profile: TranscriptWorkflowProfile) -> str:
        if workflow_profile.top_goals:
            normalized_goal_title = self._normalize_workflow_title(
                base_title=workflow_profile.top_goals[0],
                steps=steps,
                workflow_profile=workflow_profile,
            )
            if normalized_goal_title:
                return normalized_goal_title
        if workflow_profile.top_objects:
            object_name = workflow_profile.top_objects[0]
            action_name = workflow_profile.top_actions[0] if workflow_profile.top_actions else None
            normalized_object_title = self._normalize_workflow_title(
                base_title=f"{object_name} {action_name}".strip() if action_name else object_name,
                steps=steps,
                workflow_profile=workflow_profile,
            )
            if normalized_object_title:
                return normalized_object_title

        combined = " ".join(
            [
                transcript.name,
                *[str(step.get("action_text", "") or "") for step in steps[:8]],
                *[str(step.get("supporting_transcript_text", "") or "") for step in steps[:3]],
            ]
        )
        normalized = self._normalize_text(combined)

        explicit_patterns = [
            r"\b(sales order(?: creation)?)\b",
            r"\b(purchase order(?: creation)?)\b",
            r"\b(goods receipt)\b",
            r"\b(invoice(?: creation| posting)?)\b",
        ]
        for pattern in explicit_patterns:
            match = re.search(pattern, normalized)
            if match:
                return self._normalize_workflow_title(
                    base_title=match.group(1).title(),
                    steps=steps,
                    workflow_profile=workflow_profile,
                )

        signature = list(self._signature_tokens(steps))
        if signature:
            phrase = " ".join(signature[:3]).strip()
            if phrase:
                normalized_signature_title = self._normalize_workflow_title(
                    base_title=phrase.title(),
                    steps=steps,
                    workflow_profile=workflow_profile,
                )
                if normalized_signature_title:
                    return normalized_signature_title
        transcript_title = transcript.name.rsplit(".", 1)[0].strip() or "Process"
        return self._normalize_workflow_title(
            base_title=transcript_title,
            steps=steps,
            workflow_profile=workflow_profile,
        )

    def _normalize_workflow_title(
        self,
        *,
        base_title: str,
        steps: list[dict],
        workflow_profile: TranscriptWorkflowProfile,
    ) -> str:
        normalized_title = re.sub(r"\s+", " ", (base_title or "").strip()).title()
        object_name = workflow_profile.top_objects[0].title() if workflow_profile.top_objects else ""
        preferred_suffix = self._preferred_workflow_suffix(steps=steps, workflow_profile=workflow_profile)

        if object_name:
            if preferred_suffix and not normalized_title.endswith(preferred_suffix):
                if self._starts_with_non_business_action(normalized_title):
                    return f"{object_name} {preferred_suffix}".strip()
                if object_name.lower() in normalized_title.lower():
                    return f"{object_name} {preferred_suffix}".strip()
            if self._starts_with_non_business_action(normalized_title):
                return f"{object_name} {preferred_suffix or 'Process'}".strip()

        if preferred_suffix and normalized_title and not normalized_title.endswith(preferred_suffix):
            if self._starts_with_non_business_action(normalized_title):
                return f"{normalized_title.split()[-1].title()} {preferred_suffix}".strip()

        return normalized_title or "Process"

    def _preferred_workflow_suffix(self, *, steps: list[dict], workflow_profile: TranscriptWorkflowProfile) -> str:
        action_candidates = [*workflow_profile.top_actions]
        action_candidates.extend(
            self._extract_leading_action_verb(str(step.get("action_text", "") or ""))
            for step in steps[:8]
        )
        for action in action_candidates:
            if not action:
                continue
            normalized_action = action.lower().strip()
            if normalized_action in self._NON_BUSINESS_ACTIONS:
                continue
            suffix = self._WORKFLOW_SUFFIX_BY_ACTION.get(normalized_action)
            if suffix:
                return suffix
        return "Creation" if workflow_profile.top_objects else "Process"

    def _starts_with_non_business_action(self, title: str) -> bool:
        lowered = title.lower().strip()
        return any(lowered.startswith(f"{action} ") or lowered == action for action in self._NON_BUSINESS_ACTIONS)

    @staticmethod
    def _extract_leading_action_verb(action_text: str) -> str:
        match = re.match(r"^\s*([a-z]+(?:\s+[a-z]+)?)", action_text.lower())
        return match.group(1).strip() if match else ""

    def _group_summary_seed(
        self,
        *,
        inferred_title: str,
        steps: list[dict],
        notes: list[dict],
        workflow_profile: TranscriptWorkflowProfile,
    ) -> str:
        parts = [inferred_title]
        parts.extend(workflow_profile.top_actors[:2])
        parts.extend(workflow_profile.top_goals[:2])
        parts.extend(workflow_profile.top_objects[:2])
        parts.extend(workflow_profile.top_systems[:2])
        parts.extend(workflow_profile.top_rules[:2])
        parts.extend(str(step.get("action_text", "") or "") for step in steps[:6])
        parts.extend(str(note.get("text", "") or "") for note in notes[:3])
        return " ".join(part for part in parts if part).strip()

    def _refresh_group_summaries(
        self,
        *,
        process_groups: list[ProcessGroupModel],
        transcript_group_ids: dict[str, str],
        steps_by_transcript: dict[str, list[dict]],
        notes_by_transcript: dict[str, list[dict]],
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
                dict(step)
                for transcript_id in transcript_ids
                for step in steps_by_transcript.get(transcript_id, [])
            ]
            group_notes = [
                dict(note)
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
            ai_summary = self.ai_transcript_interpreter.summarize_process_group(
                process_title=process_group.title,
                workflow_summary=workflow_summary,
                steps=group_steps,
                notes=group_notes,
                document_type=document_type,
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
        steps: list[dict],
        notes: list[dict],
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
        steps: list[dict],
        notes: list[dict],
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
        ai_capabilities = self.ai_transcript_interpreter.classify_workflow_capabilities(
            process_title=process_title,
            workflow_summary=workflow_summary,
            document_type=document_type,
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
        steps: list[dict],
        notes: list[dict],
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

    def _signature_tokens(self, steps: list[dict]) -> set[str]:
        text = " ".join(str(step.get("action_text", "") or "") for step in steps[:12])
        tokens = [token for token in self._normalize_text(text).split() if token and token not in self._STOPWORDS]
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return {token for token, _ in ordered[:5]}

    def _operation_signature_from_steps(self, steps: list[dict]) -> list[str]:
        signature: list[str] = []
        seen: set[str] = set()
        for step in steps[:8]:
            action_text = str(step.get("action_text", "") or "").strip()
            if not action_text:
                continue
            normalized = self._normalize_text(action_text)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            signature.append(action_text)
            if len(signature) >= 5:
                break
        return signature

    def _serialize_existing_groups_for_ai(
        self,
        *,
        existing_groups: list[ProcessGroupModel],
        heuristic_match: HeuristicGroupMatchResult,
    ) -> list[dict[str, object]]:
        candidate_scores: dict[str, CandidateMatchRecord] = {
            str(item.get("group_title", "")): item
            for item in heuristic_match["candidate_matches"]
        }
        serialized: list[dict[str, object]] = []
        for group in existing_groups:
            candidate_score = candidate_scores.get(group.title)
            serialized.append(
                {
                    "title": group.title,
                    "canonical_slug": group.canonical_slug,
                    "summary_text": getattr(group, "summary_text", "") or "",
                    "capability_tags": self._parse_capability_tags(getattr(group, "capability_tags_json", "[]")),
                    "summary_tokens": [
                        token
                        for token in self._normalize_text(getattr(group, "summary_text", "") or "").split()
                        if token and token not in self._STOPWORDS
                    ][:10],
                    "heuristic_score": candidate_score.get("score") if candidate_score is not None else None,
                    "heuristic_title_ratio": candidate_score.get("title_ratio") if candidate_score is not None else None,
                    "heuristic_signature_overlap": candidate_score.get("signature_overlap") if candidate_score is not None else None,
                    "heuristic_system_alignment": candidate_score.get("system_alignment") if candidate_score is not None else None,
                    "heuristic_application_alignment": candidate_score.get("application_alignment") if candidate_score is not None else None,
                }
            )
        return serialized

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
        normalized = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
        return re.sub(r"\s+", " ", normalized).strip()

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9\s-]+", " ", value.lower())
        collapsed = re.sub(r"\s+", "-", normalized.strip())
        return re.sub(r"-{2,}", "-", collapsed).strip("-") or "process"

    @staticmethod
    def _build_transcript_profiles(
        *,
        evidence_segments: list[EvidenceSegment],
        workflow_boundary_decisions: list[WorkflowBoundaryDecision],
        steps_by_transcript: dict[str, list[dict]],
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
                leading_action = ProcessGroupingService._extract_leading_action_verb(action_text)
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
        parts = [
            *profile.top_actors,
            *profile.top_objects,
            *profile.top_systems,
            *profile.top_applications,
            *profile.top_actions,
            *profile.top_goals,
            *profile.top_rules,
            *profile.top_domain_terms,
        ]
        normalized = self._normalize_text(" ".join(parts))
        return {token for token in normalized.split() if token and token not in self._STOPWORDS}
