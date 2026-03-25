r"""
Purpose: Assign transcript outputs into logical process groups within a session.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\process_grouping_service.py
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.core.observability import get_logger
from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.process_group import ProcessGroupModel
from app.services.process_group_service import ProcessGroupService
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter, WorkflowGroupMatchInterpretation, WorkflowTitleInterpretation
from worker.services.workflow_intelligence import EvidenceSegment, WorkflowBoundaryDecision

logger = get_logger(__name__)


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
    candidate_matches: list[dict[str, object]]
    supporting_signals: list[str]


class ProcessGroupingService:
    """Cluster transcript outputs into same-process vs different-process groups."""

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
                    top_actions=[],
                    top_goals=[],
                    top_rules=[],
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
                    "assigned_group_title": matched_group.title,
                    "decision": resolution.decision,
                    "decision_confidence": resolution.confidence,
                    "decision_source": resolution.decision_source,
                    "is_ambiguous": resolution.is_ambiguous,
                    "rationale": resolution.rationale,
                    "candidate_matches": resolution.candidate_matches,
                    "supporting_signals": resolution.supporting_signals,
                    "top_goals": workflow_profile.top_goals,
                    "top_objects": workflow_profile.top_objects,
                    "top_systems": workflow_profile.top_systems,
                    "top_actors": workflow_profile.top_actors,
                    "top_rules": workflow_profile.top_rules,
                }
            )
            for step in transcript_steps:
                step["process_group_id"] = matched_group.id
            for note in transcript_notes:
                note["process_group_id"] = matched_group.id

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
        ai_group_match = self._match_existing_group_with_ai(
            transcript=transcript,
            title_resolution=title_resolution,
            workflow_profile=workflow_profile,
            steps=steps,
            notes=notes,
            existing_groups=existing_groups,
        )
        if ai_group_match is not None:
            return ai_group_match
        match_result = self._match_existing_group(
            slug=slug,
            title=title,
            steps=steps,
            workflow_profile=workflow_profile,
            existing_groups=existing_groups,
        )
        matched_group = match_result["matched_group"]
        ambiguity = match_result["ambiguity"]
        candidate_matches = match_result["candidate_matches"]
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
        if matched_group is not None:
            return GroupResolutionDecision(
                inferred_title=title,
                inferred_slug=slug,
                matched_group=matched_group,
                decision="matched_existing_group" if not ambiguity else "ambiguously_matched_existing_group",
                confidence="high" if match_result["best_score"] >= 0.9 else "medium",
                decision_source="heuristic",
                is_ambiguous=ambiguity,
                rationale=(
                    f"Matched to existing workflow '{matched_group.title}' using title and profile overlap."
                    if not ambiguity
                    else f"Matched to existing workflow '{matched_group.title}', but another plausible workflow also scored closely."
                ),
                candidate_matches=candidate_matches,
                supporting_signals=[*title_supporting_signals, *match_result["supporting_signals"]],
            )
        return GroupResolutionDecision(
            inferred_title=title,
            inferred_slug=slug,
            matched_group=None,
            decision="created_new_group" if not ambiguity else "ambiguously_created_new_group",
            confidence="medium" if ambiguity else "high",
            decision_source="heuristic",
            is_ambiguous=ambiguity,
            rationale=(
                f"No strong existing workflow match was found for inferred workflow '{title}'."
                if not ambiguity
                else f"No confident workflow match was found for inferred workflow '{title}', so a new group was created conservatively."
            ),
            candidate_matches=candidate_matches,
            supporting_signals=[*title_supporting_signals, *match_result["supporting_signals"]],
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
        if ai_resolution is None or ai_resolution.confidence not in {"high", "medium"}:
            return WorkflowTitleInterpretation(
                workflow_title=fallback_title,
                canonical_slug=self._slugify(fallback_title),
                confidence="medium",
                rationale="",
            )
        return WorkflowTitleInterpretation(
            workflow_title=ai_resolution.workflow_title.strip() or fallback_title,
            canonical_slug=self._slugify(ai_resolution.canonical_slug or ai_resolution.workflow_title or fallback_title),
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
            existing_groups=[
                {
                    "title": group.title,
                    "canonical_slug": group.canonical_slug,
                    "summary_text": getattr(group, "summary_text", "") or "",
                }
                for group in existing_groups
            ],
        )
        if ai_match is None:
            return None
        if ai_match.confidence == "high":
            return self._build_ai_group_match_decision(
                ai_match=ai_match,
                fallback_title=title_resolution.workflow_title,
                existing_groups=existing_groups,
            )
        if ai_match.confidence == "medium":
            heuristic_match = self._match_existing_group(
                slug=title_resolution.canonical_slug,
                title=title_resolution.workflow_title,
                steps=steps,
                workflow_profile=workflow_profile,
                existing_groups=existing_groups,
            )
            heuristic_title = heuristic_match["matched_group"].title if heuristic_match["matched_group"] is not None else None
            if heuristic_title == ai_match.matched_existing_title:
                return self._build_ai_group_match_decision(
                    ai_match=ai_match,
                    fallback_title=title_resolution.workflow_title,
                    existing_groups=existing_groups,
                )
            if heuristic_match["matched_group"] is None and ai_match.matched_existing_title is None:
                return self._build_ai_group_match_decision(
                    ai_match=ai_match,
                    fallback_title=title_resolution.workflow_title,
                    existing_groups=existing_groups,
                )
        return None

    def _build_ai_group_match_decision(
        self,
        *,
        ai_match: WorkflowGroupMatchInterpretation,
        fallback_title: str,
        existing_groups: list[ProcessGroupModel],
    ) -> GroupResolutionDecision:
        matched_group = next(
            (group for group in existing_groups if group.title == ai_match.matched_existing_title),
            None,
        )
        resolved_title = ai_match.recommended_title.strip() or fallback_title
        resolved_slug = self._slugify(ai_match.recommended_slug or resolved_title)
        if matched_group is not None:
            return GroupResolutionDecision(
                inferred_title=resolved_title,
                inferred_slug=resolved_slug,
                matched_group=matched_group,
                decision="ai_matched_existing_group",
                confidence=ai_match.confidence,
                decision_source="ai",
                is_ambiguous=False,
                rationale=ai_match.rationale or f"AI matched this transcript to existing workflow '{matched_group.title}'.",
                candidate_matches=[{"group_title": matched_group.title, "score": ai_match.confidence}],
                supporting_signals=["ai_group_matcher"],
            )
        return GroupResolutionDecision(
            inferred_title=resolved_title,
            inferred_slug=resolved_slug,
            matched_group=None,
            decision="ai_created_new_group",
            confidence=ai_match.confidence,
            decision_source="ai",
            is_ambiguous=False,
            rationale=ai_match.rationale or f"AI determined this transcript should create workflow '{resolved_title}'.",
            candidate_matches=[],
            supporting_signals=["ai_group_matcher"],
        )

    def _resolve_ambiguity_with_ai(
        self,
        *,
        transcript: ArtifactModel,
        inferred_title: str,
        candidate_matches: list[dict[str, object]],
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
    ) -> dict[str, object]:
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
        candidate_scores: list[dict[str, object]] = []
        for group in existing_groups:
            title_ratio = SequenceMatcher(None, normalized_title, self._normalize_text(group.title)).ratio()
            signature_overlap = 0.0
            if getattr(group, "summary_text", ""):
                group_tokens = {token for token in self._normalize_text(group.summary_text).split() if token and token not in self._STOPWORDS}
                signature_overlap = len(candidate_signature & group_tokens) / max(len(candidate_signature | group_tokens), 1)
                profile_overlap = len(profile_tokens & group_tokens) / max(len(profile_tokens | group_tokens), 1) if profile_tokens else 0.0
            else:
                profile_overlap = 0.0
            score = (title_ratio * 0.65) + (signature_overlap * 0.2) + (profile_overlap * 0.15)
            candidate_scores.append(
                {
                    "group_title": group.title,
                    "score": round(score, 3),
                    "title_ratio": round(title_ratio, 3),
                    "signature_overlap": round(signature_overlap, 3),
                    "profile_overlap": round(profile_overlap, 3),
                }
            )
            if score > best_score:
                second_best_score = best_score
                best_score = score
                best_group = group
            elif score > second_best_score:
                second_best_score = score

        candidate_scores.sort(key=lambda item: float(item["score"]), reverse=True)
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
            "matched_group": best_group if best_score >= 0.82 else None,
            "best_score": best_score,
            "ambiguity": ambiguity,
            "candidate_matches": candidate_scores[:3],
            "supporting_signals": supporting_signals,
        }

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
            "top_actions": workflow_profile.top_actions,
            "top_goals": workflow_profile.top_goals,
            "top_rules": workflow_profile.top_rules,
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

    @staticmethod
    def _sort_transcripts(transcript_artifacts: list[ArtifactModel]) -> list[ArtifactModel]:
        return sorted(
            transcript_artifacts,
            key=lambda artifact: (
                getattr(getattr(artifact, "meeting", None), "order_index", None)
                if getattr(getattr(artifact, "meeting", None), "order_index", None) is not None
                else 1_000_000,
                getattr(getattr(artifact, "meeting", None), "meeting_date", None).isoformat()
                if getattr(getattr(artifact, "meeting", None), "meeting_date", None) is not None
                else "",
                getattr(getattr(artifact, "meeting", None), "uploaded_at", None).isoformat()
                if getattr(getattr(artifact, "meeting", None), "uploaded_at", None) is not None
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
    ) -> dict[str, TranscriptWorkflowProfile]:
        segments_by_id = {segment.id: segment for segment in evidence_segments}
        object_counts: dict[str, Counter[str]] = defaultdict(Counter)
        actor_counts: dict[str, Counter[str]] = defaultdict(Counter)
        system_counts: dict[str, Counter[str]] = defaultdict(Counter)
        action_counts: dict[str, Counter[str]] = defaultdict(Counter)
        goal_counts: dict[str, Counter[str]] = defaultdict(Counter)
        rule_counts: dict[str, Counter[str]] = defaultdict(Counter)

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

        boundary_map: dict[str, tuple[str, str]] = {}
        for decision in workflow_boundary_decisions:
            left_segment = segments_by_id.get(decision.left_segment_id)
            right_segment = segments_by_id.get(decision.right_segment_id)
            if left_segment is None or right_segment is None:
                continue
            if left_segment.transcript_artifact_id == right_segment.transcript_artifact_id:
                continue
            boundary_map[left_segment.transcript_artifact_id] = (decision.decision, decision.confidence)

        transcript_ids = {segment.transcript_artifact_id for segment in evidence_segments}
        profiles: dict[str, TranscriptWorkflowProfile] = {}
        for transcript_id in transcript_ids:
            boundary = boundary_map.get(transcript_id)
            profiles[transcript_id] = TranscriptWorkflowProfile(
                transcript_artifact_id=transcript_id,
                top_actors=[value for value, _ in actor_counts[transcript_id].most_common(3)],
                top_objects=[value for value, _ in object_counts[transcript_id].most_common(3)],
                top_systems=[value for value, _ in system_counts[transcript_id].most_common(3)],
                top_actions=[value for value, _ in action_counts[transcript_id].most_common(3)],
                top_goals=[value for value, _ in goal_counts[transcript_id].most_common(3)],
                top_rules=[value for value, _ in rule_counts[transcript_id].most_common(2)],
                boundary_to_next=boundary[0] if boundary else None,
                boundary_to_next_confidence=boundary[1] if boundary else None,
            )
        return profiles

    def _profile_tokens(self, profile: TranscriptWorkflowProfile) -> set[str]:
        parts = [
            *profile.top_actors,
            *profile.top_objects,
            *profile.top_systems,
            *profile.top_actions,
            *profile.top_goals,
            *profile.top_rules,
        ]
        normalized = self._normalize_text(" ".join(parts))
        return {token for token in normalized.split() if token and token not in self._STOPWORDS}
