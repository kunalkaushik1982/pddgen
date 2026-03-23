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
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
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
    is_ambiguous: bool
    rationale: str
    candidate_matches: list[dict[str, object]]
    supporting_signals: list[str]


class ProcessGroupingService:
    """Cluster transcript outputs into same-process vs different-process groups."""

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
        slug = self._slugify(title)
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
                is_ambiguous=ambiguity,
                rationale=(
                    f"Matched to existing workflow '{matched_group.title}' using title and profile overlap."
                    if not ambiguity
                    else f"Matched to existing workflow '{matched_group.title}', but another plausible workflow also scored closely."
                ),
                candidate_matches=candidate_matches,
                supporting_signals=match_result["supporting_signals"],
            )
        return GroupResolutionDecision(
            inferred_title=title,
            inferred_slug=slug,
            matched_group=None,
            decision="created_new_group" if not ambiguity else "ambiguously_created_new_group",
            confidence="medium" if ambiguity else "high",
            is_ambiguous=ambiguity,
            rationale=(
                f"No strong existing workflow match was found for inferred workflow '{title}'."
                if not ambiguity
                else f"No confident workflow match was found for inferred workflow '{title}', so a new group was created conservatively."
            ),
            candidate_matches=candidate_matches,
            supporting_signals=match_result["supporting_signals"],
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
            return workflow_profile.top_goals[0]
        if workflow_profile.top_objects:
            object_name = workflow_profile.top_objects[0]
            action_name = workflow_profile.top_actions[0] if workflow_profile.top_actions else None
            if action_name:
                return f"{object_name} {action_name}".strip().title()
            return object_name.title()

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
                return match.group(1).title()

        signature = list(self._signature_tokens(steps))
        if signature:
            phrase = " ".join(signature[:3]).strip()
            if phrase:
                return phrase.title()
        return transcript.name.rsplit(".", 1)[0].strip() or "Process"

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
