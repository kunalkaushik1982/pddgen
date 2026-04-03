r"""
Purpose: Lightweight transcript segmentation and semantic enrichment for workflow-intelligence groundwork.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\evidence_segmentation_service.py
"""

from __future__ import annotations

import logging
import re
from uuid import uuid4

from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
from worker.services.ai_skills.semantic_enrichment.schemas import SemanticEnrichmentRequest
from worker.services.ai_skills.semantic_enrichment.skill import SemanticEnrichmentSkill
from worker.services.ai_skills.workflow_boundary_detection.schemas import WorkflowBoundaryDetectionRequest
from worker.services.ai_skills.workflow_boundary_detection.skill import WorkflowBoundaryDetectionSkill
from worker.services.draft_generation.support import ACTION_VERB_PATTERNS, TIMESTAMP_PATTERN, classify_action_type
from worker.services.workflow_intelligence.strategy_interfaces import WorkflowIntelligenceStrategySet
from worker.services.workflow_intelligence import EvidenceSegment, SemanticEnrichment, WorkflowBoundaryDecision

logger = logging.getLogger(__name__)


class _InterpreterSemanticEnrichmentSkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.skill_id = "semantic_enrichment_interpreter_adapter"
        self.version = "interpreter-adapter"

    def run(self, input):  # type: ignore[no-untyped-def]
        return self._interpreter.enrich_workflow_segment(
            transcript_name=input.transcript_name,
            segment_text=input.segment_text,
            segment_context=input.segment_context,
        )


class _InterpreterWorkflowBoundarySkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.skill_id = "workflow_boundary_interpreter_adapter"
        self.version = "interpreter-adapter"

    def run(self, input):  # type: ignore[no-untyped-def]
        return self._interpreter.classify_workflow_boundary(
            left_segment=input.left_segment,
            right_segment=input.right_segment,
        )


class ParagraphTranscriptSegmentationStrategy:
    """Default transcript chunking strategy based on paragraph and timestamp continuity."""

    strategy_key = "paragraph_v1"

    def segment(
        self,
        *,
        transcript_artifact_id: str,
        meeting_id: str | None,
        transcript_text: str,
    ) -> list[EvidenceSegment]:
        chunks = [chunk.strip() for chunk in re.split(r"(?:\r?\n){2,}", transcript_text) if chunk.strip()]
        if not chunks:
            chunks = [line.strip() for line in transcript_text.splitlines() if line.strip()]

        segments: list[EvidenceSegment] = []
        for index, chunk in enumerate(chunks, start=1):
            timestamps = self._extract_timestamps(chunk)
            segments.append(
                EvidenceSegment(
                    id=str(uuid4()),
                    transcript_artifact_id=transcript_artifact_id,
                    meeting_id=meeting_id,
                    segment_order=index,
                    text=chunk,
                    start_timestamp=timestamps[0] if timestamps else None,
                    end_timestamp=timestamps[-1] if timestamps else None,
                    segmentation_method="timestamp_paragraph" if timestamps else "paragraph_fallback",
                    confidence="medium" if timestamps else "low",
                )
            )
        return segments

    @staticmethod
    def _extract_timestamps(text: str) -> list[str]:
        timestamps: list[str] = []
        for match in TIMESTAMP_PATTERN.finditer(text):
            hours_group, minutes_group, seconds_group = match.groups()
            hours = int(hours_group or 0)
            minutes = int(minutes_group)
            seconds = int(seconds_group)
            timestamps.append(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        return timestamps


class HeuristicSemanticEnrichmentStrategy:
    """Default semantic enrichment strategy using lightweight text heuristics."""

    strategy_key = "heuristic_v2"

    SYSTEM_PATTERNS = (
        re.compile(r"\b(sap gui|sap|oracle|salesforce|sfdc|excel|outlook|portal|application|app)\b", re.IGNORECASE),
        re.compile(r"\b(transaction code|t[\-\s]?code|screen|menu|form)\b", re.IGNORECASE),
    )
    OBJECT_PATTERN = re.compile(
        r"\b(purchase order|sales order|vendor master|vendor|invoice|claim|patient record|patient|matter|contract|account|record|case|order|request)\b",
        re.IGNORECASE,
    )
    ACTOR_PATTERNS = (
        (re.compile(r"\b(user|operator|analyst|employee|processor)\b", re.IGNORECASE), "operator"),
        (re.compile(r"\b(approver|reviewer|manager|lead)\b", re.IGNORECASE), "approver"),
        (re.compile(r"\b(customer|client|patient|vendor)\b", re.IGNORECASE), "external_party"),
        (re.compile(r"\b(system|application)\b", re.IGNORECASE), "system"),
    )
    RULE_PATTERNS = (
        re.compile(r"\bmust\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bshould\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\brequired\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bvalidate\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\breview\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bensure\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bif\b.*?(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bbefore\b.*?(?:\.|$)", re.IGNORECASE),
    )
    DOMAIN_STOPWORDS = {
        "the",
        "and",
        "then",
        "into",
        "from",
        "with",
        "that",
        "this",
        "your",
        "their",
        "record",
        "screen",
        "field",
        "system",
        "application",
        "process",
        "transaction",
        "details",
        "review",
        "validate",
    }

    def enrich(self, segment: EvidenceSegment) -> SemanticEnrichment:
        lowered = segment.text.lower()
        action_verb = next(
            (
                pattern
                for patterns in ACTION_VERB_PATTERNS.values()
                for pattern in patterns
                if pattern in lowered
            ),
            None,
        )
        action_type = classify_action_type(segment.text)
        system_name = self._extract_system_name(segment.text)
        object_match = self.OBJECT_PATTERN.search(segment.text)
        actor, actor_role = self._extract_actor(segment.text)
        business_object = object_match.group(1).title() if object_match else None
        workflow_goal = self._build_workflow_goal(action_verb, business_object)
        rule_hints = self._extract_rule_hints(segment.text)
        domain_terms = self._extract_domain_terms(segment.text, business_object=business_object)
        signal_count = sum(
            1
            for item in (actor, system_name, action_verb, business_object, workflow_goal)
            if item
        ) + len(rule_hints)
        return SemanticEnrichment(
            actor=actor,
            actor_role=actor_role,
            system_name=system_name,
            action_verb=action_verb,
            action_type=action_type,
            business_object=business_object,
            workflow_goal=workflow_goal,
            rule_hints=rule_hints,
            domain_terms=domain_terms,
            confidence=self._confidence_from_signal_count(signal_count),
            enrichment_source="heuristic",
        )

    def _extract_system_name(self, text: str) -> str | None:
        for pattern in self.SYSTEM_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).upper()
        return None

    def _extract_actor(self, text: str) -> tuple[str | None, str | None]:
        for pattern, actor_role in self.ACTOR_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).title(), actor_role
        return None, None

    @staticmethod
    def _build_workflow_goal(action_verb: str | None, business_object: str | None) -> str | None:
        if action_verb and business_object:
            return f"{action_verb.title()} {business_object}".strip()
        return business_object

    def _extract_rule_hints(self, text: str) -> list[str]:
        rule_hints: list[str] = []
        for pattern in self.RULE_PATTERNS:
            for match in pattern.findall(text):
                normalized = re.sub(r"\s+", " ", match.strip().rstrip("."))
                if normalized and normalized not in rule_hints:
                    rule_hints.append(normalized)
        return rule_hints[:4]

    def _extract_domain_terms(self, text: str, *, business_object: str | None) -> list[str]:
        normalized = re.sub(r"[^a-z0-9\s]+", " ", text.lower())
        tokens = [token for token in normalized.split() if len(token) > 3 and token not in self.DOMAIN_STOPWORDS]
        ordered_terms: list[str] = []
        seen: set[str] = set()
        if business_object:
            normalized_object = business_object.lower()
            ordered_terms.append(normalized_object)
            seen.add(normalized_object)
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            ordered_terms.append(token)
            if len(ordered_terms) >= 6:
                break
        return ordered_terms

    @staticmethod
    def _confidence_from_signal_count(signal_count: int) -> str:
        if signal_count >= 5:
            return "high"
        if signal_count >= 2:
            return "medium"
        return "low"


class HeuristicWorkflowBoundaryStrategy:
    """Default adjacent-segment continuity strategy using shared object/system signals."""

    strategy_key = "heuristic_v2"

    def decide(self, left: EvidenceSegment, right: EvidenceSegment) -> WorkflowBoundaryDecision:
        left_enrichment = left.enrichment
        right_enrichment = right.enrichment
        if left_enrichment is None or right_enrichment is None:
            return WorkflowBoundaryDecision(
                left_segment_id=left.id,
                right_segment_id=right.id,
                decision="uncertain",
                confidence="low",
                reason="One or both segments did not contain enrichment signals.",
                decision_source="heuristic",
                heuristic_decision="uncertain",
                heuristic_confidence="low",
            )

        overlap_score = 0.0
        reasons: list[str] = []

        if left_enrichment.business_object and left_enrichment.business_object == right_enrichment.business_object:
            overlap_score += 0.45
            reasons.append(f"shared object '{left_enrichment.business_object}'")
        elif left_enrichment.business_object and right_enrichment.business_object:
            overlap_score -= 0.35
            reasons.append("different business objects")

        if left_enrichment.workflow_goal and left_enrichment.workflow_goal == right_enrichment.workflow_goal:
            overlap_score += 0.3
            reasons.append(f"shared goal '{left_enrichment.workflow_goal}'")
        elif left_enrichment.workflow_goal and right_enrichment.workflow_goal:
            overlap_score -= 0.2
            reasons.append("different workflow goals")

        if left_enrichment.system_name and left_enrichment.system_name == right_enrichment.system_name:
            overlap_score += 0.2
            reasons.append(f"shared system '{left_enrichment.system_name}'")

        if left_enrichment.action_type and left_enrichment.action_type == right_enrichment.action_type:
            overlap_score += 0.1
            reasons.append(f"shared action type '{left_enrichment.action_type}'")

        left_terms = set(left_enrichment.domain_terms)
        right_terms = set(right_enrichment.domain_terms)
        if left_terms and right_terms:
            shared_terms = left_terms & right_terms
            if shared_terms:
                overlap_score += min(0.2, 0.05 * len(shared_terms))
                reasons.append("shared domain terms: " + ", ".join(sorted(shared_terms)[:3]))

        if self._has_explicit_new_workflow_marker(right.text):
            overlap_score -= 0.4
            reasons.append("explicit new-workflow marker in right segment")

        if self._is_timestamp_contiguous(left, right):
            overlap_score += 0.05
            reasons.append("contiguous evidence timing")

        if overlap_score >= 0.45:
            decision = "same_workflow"
            confidence = "high" if overlap_score >= 0.7 else "medium"
        elif overlap_score <= -0.2:
            decision = "new_workflow"
            confidence = "medium"
        else:
            decision = "uncertain"
            confidence = "low" if overlap_score < 0.2 else "medium"

        reason = "; ".join(reasons) if reasons else "No clear continuity signal."
        return WorkflowBoundaryDecision(
            left_segment_id=left.id,
            right_segment_id=right.id,
            decision=decision,
            confidence=confidence,
            reason=reason,
            decision_source="heuristic",
            heuristic_decision=decision,
            heuristic_confidence=confidence,
        )

    @staticmethod
    def _has_explicit_new_workflow_marker(text: str) -> bool:
        normalized = text.lower()
        markers = (
            "now we will create",
            "next we will create",
            "moving to",
            "switch to",
            "another process",
            "different process",
            "new workflow",
        )
        return any(marker in normalized for marker in markers)

    @staticmethod
    def _is_timestamp_contiguous(left: EvidenceSegment, right: EvidenceSegment) -> bool:
        if not left.end_timestamp or not right.start_timestamp:
            return False
        return left.end_timestamp == right.start_timestamp


class AISemanticEnrichmentStrategy:
    """AI-first segment enrichment strategy with deterministic fallback."""

    strategy_key = "ai_plus_heuristic_v1"

    def __init__(
        self,
        *,
        ai_transcript_interpreter: AITranscriptInterpreter | None = None,
        fallback_strategy: HeuristicSemanticEnrichmentStrategy | None = None,
    ) -> None:
        self.ai_transcript_interpreter = ai_transcript_interpreter or AITranscriptInterpreter()
        self.fallback_strategy = fallback_strategy or HeuristicSemanticEnrichmentStrategy()
        self._semantic_enrichment_skill = (
            _InterpreterSemanticEnrichmentSkill(self.ai_transcript_interpreter)
            if ai_transcript_interpreter is not None
            else SemanticEnrichmentSkill()
        )

    def enrich(self, segment: EvidenceSegment) -> SemanticEnrichment:
        fallback_enrichment = self.fallback_strategy.enrich(segment)
        logger.info(
            "Delegating semantic enrichment to AI skill.",
            extra={
                "skill_id": self._semantic_enrichment_skill.skill_id,
                "skill_version": self._semantic_enrichment_skill.version,
                "segment_id": segment.id,
                "transcript_artifact_id": segment.transcript_artifact_id,
            },
        )
        ai_result = self._semantic_enrichment_skill.run(
            SemanticEnrichmentRequest(
                transcript_name=segment.transcript_artifact_id,
                segment_text=segment.text,
                segment_context={
                    "segment_order": segment.segment_order,
                    "start_timestamp": segment.start_timestamp or "",
                    "end_timestamp": segment.end_timestamp or "",
                    "segmentation_method": segment.segmentation_method,
                },
            )
        )
        if ai_result is None:
            return fallback_enrichment

        if ai_result.confidence not in {"high", "medium"}:
            fallback_enrichment.enrichment_source = "heuristic_fallback"
            return fallback_enrichment

        resolved = SemanticEnrichment(
            actor=ai_result.actor or fallback_enrichment.actor,
            actor_role=ai_result.actor_role or fallback_enrichment.actor_role,
            system_name=ai_result.system_name or fallback_enrichment.system_name,
            action_verb=ai_result.action_verb or fallback_enrichment.action_verb,
            action_type=ai_result.action_type or fallback_enrichment.action_type,
            business_object=ai_result.business_object or fallback_enrichment.business_object,
            workflow_goal=ai_result.workflow_goal or fallback_enrichment.workflow_goal,
            rule_hints=ai_result.rule_hints or fallback_enrichment.rule_hints,
            domain_terms=ai_result.domain_terms or fallback_enrichment.domain_terms,
            confidence=ai_result.confidence,
            enrichment_source="ai",
        )
        if not self._has_meaningful_ai_signal(resolved):
            fallback_enrichment.enrichment_source = "heuristic_fallback"
            return fallback_enrichment
        return resolved

    @staticmethod
    def _has_meaningful_ai_signal(enrichment: SemanticEnrichment) -> bool:
        return any(
            (
                enrichment.business_object,
                enrichment.workflow_goal,
                enrichment.system_name,
                enrichment.action_verb,
                enrichment.actor,
            )
        ) or bool(enrichment.domain_terms)


class AIWorkflowBoundaryStrategy:
    """AI-first adjacent-segment continuity strategy with deterministic fallback."""

    strategy_key = "ai_plus_heuristic_v1"

    def __init__(
        self,
        *,
        ai_transcript_interpreter: AITranscriptInterpreter | None = None,
        fallback_strategy: HeuristicWorkflowBoundaryStrategy | None = None,
    ) -> None:
        self.ai_transcript_interpreter = ai_transcript_interpreter or AITranscriptInterpreter()
        self.fallback_strategy = fallback_strategy or HeuristicWorkflowBoundaryStrategy()
        self._workflow_boundary_skill = (
            _InterpreterWorkflowBoundarySkill(self.ai_transcript_interpreter)
            if ai_transcript_interpreter is not None
            else WorkflowBoundaryDetectionSkill()
        )

    def decide(self, left: EvidenceSegment, right: EvidenceSegment) -> WorkflowBoundaryDecision:
        fallback_decision = self.fallback_strategy.decide(left, right)
        logger.info(
            "Delegating workflow boundary detection to AI skill.",
            extra={
                "skill_id": self._workflow_boundary_skill.skill_id,
                "skill_version": self._workflow_boundary_skill.version,
                "left_segment_id": left.id,
                "right_segment_id": right.id,
            },
        )
        ai_result = self._workflow_boundary_skill.run(
            WorkflowBoundaryDetectionRequest(
                left_segment=self._serialize_segment(left),
                right_segment=self._serialize_segment(right),
            )
        )
        if ai_result is None:
            return fallback_decision

        ai_confidence = ai_result.confidence
        if ai_confidence not in {"high", "medium"}:
            fallback_decision.decision_source = "heuristic_fallback"
            fallback_decision.ai_decision = ai_result.decision
            fallback_decision.ai_confidence = ai_result.confidence
            return fallback_decision

        heuristic_decision = fallback_decision.decision
        heuristic_confidence = fallback_decision.confidence
        conflict_detected = heuristic_decision != ai_result.decision
        ai_reason = ai_result.rationale.strip() or fallback_decision.reason

        if not conflict_detected:
            return WorkflowBoundaryDecision(
                left_segment_id=left.id,
                right_segment_id=right.id,
                decision=ai_result.decision,
                confidence=ai_confidence,
                reason=ai_reason,
                decision_source="ai",
                heuristic_decision=heuristic_decision,
                heuristic_confidence=heuristic_confidence,
                ai_decision=ai_result.decision,
                ai_confidence=ai_confidence,
                conflict_detected=False,
            )

        resolved = self._resolve_conflict(
            left=left,
            right=right,
            heuristic_decision=fallback_decision,
            ai_decision=ai_result,
        )
        resolved.heuristic_decision = heuristic_decision
        resolved.heuristic_confidence = heuristic_confidence
        resolved.ai_decision = ai_result.decision
        resolved.ai_confidence = ai_confidence
        resolved.conflict_detected = True
        return resolved

    def _resolve_conflict(
        self,
        *,
        left: EvidenceSegment,
        right: EvidenceSegment,
        heuristic_decision: WorkflowBoundaryDecision,
        ai_decision,
    ) -> WorkflowBoundaryDecision:
        heuristic_confidence = heuristic_decision.confidence
        ai_confidence = ai_decision.confidence

        if ai_confidence == "high" and heuristic_confidence != "high":
            return WorkflowBoundaryDecision(
                left_segment_id=left.id,
                right_segment_id=right.id,
                decision=ai_decision.decision,
                confidence=ai_confidence,
                reason=(
                    "AI boundary decision overrode a weaker heuristic decision. "
                    f"AI rationale: {ai_decision.rationale.strip() or 'No AI rationale provided.'}"
                ),
                decision_source="ai_conflict_override",
            )

        if heuristic_confidence == "high" and ai_confidence != "high":
            heuristic_decision.decision_source = "heuristic_fallback"
            heuristic_decision.reason = (
                "Heuristic boundary decision was kept because it had stronger confidence than the conflicting AI result. "
                f"Heuristic rationale: {heuristic_decision.reason}"
            )
            return heuristic_decision

        return WorkflowBoundaryDecision(
            left_segment_id=left.id,
            right_segment_id=right.id,
            decision="uncertain",
            confidence="medium" if ai_confidence == "high" or heuristic_confidence == "high" else "low",
            reason=(
                "AI and heuristic workflow-boundary classifiers disagreed and neither result was strong enough to win decisively. "
                f"Heuristic said {heuristic_decision.decision} ({heuristic_confidence}); "
                f"AI said {ai_decision.decision} ({ai_confidence})."
            ),
            decision_source="conflict_unresolved",
        )

    @staticmethod
    def _serialize_segment(segment: EvidenceSegment) -> dict[str, object]:
        enrichment = segment.enrichment
        return {
            "id": segment.id,
            "transcript_artifact_id": segment.transcript_artifact_id,
            "segment_order": segment.segment_order,
            "text": segment.text,
            "start_timestamp": segment.start_timestamp,
            "end_timestamp": segment.end_timestamp,
            "segmentation_method": segment.segmentation_method,
            "workflow_summary": {
                "actor": enrichment.actor if enrichment else None,
                "system_name": enrichment.system_name if enrichment else None,
                "action_type": enrichment.action_type if enrichment else None,
                "business_object": enrichment.business_object if enrichment else None,
                "workflow_goal": enrichment.workflow_goal if enrichment else None,
                "domain_terms": enrichment.domain_terms if enrichment else [],
                "rule_hints": enrichment.rule_hints if enrichment else [],
            },
            "enrichment": {
                "actor": enrichment.actor if enrichment else None,
                "actor_role": enrichment.actor_role if enrichment else None,
                "system_name": enrichment.system_name if enrichment else None,
                "action_verb": enrichment.action_verb if enrichment else None,
                "action_type": enrichment.action_type if enrichment else None,
                "business_object": enrichment.business_object if enrichment else None,
                "workflow_goal": enrichment.workflow_goal if enrichment else None,
                "rule_hints": enrichment.rule_hints if enrichment else [],
                "domain_terms": enrichment.domain_terms if enrichment else [],
                "confidence": enrichment.confidence if enrichment else "unknown",
            },
        }


class EvidenceSegmentationService:
    """Orchestrate segmentation, enrichment, and boundary detection via explicit strategies."""

    def __init__(
        self,
        *,
        strategy_set: WorkflowIntelligenceStrategySet,
    ) -> None:
        self.segmenter = strategy_set.segmenter
        self.enricher = strategy_set.enricher
        self.boundary_detector = strategy_set.boundary_detector

    def segment_transcript(
        self,
        *,
        transcript_artifact_id: str,
        meeting_id: str | None,
        transcript_text: str,
    ) -> list[EvidenceSegment]:
        """Produce ordered evidence segments from one normalized transcript."""
        segments = self.segmenter.segment(
            transcript_artifact_id=transcript_artifact_id,
            meeting_id=meeting_id,
            transcript_text=transcript_text,
        )
        for segment in segments:
            segment.enrichment = self.enricher.enrich(segment)
        return segments

    def infer_boundary_decisions(self, segments: list[EvidenceSegment]) -> list[WorkflowBoundaryDecision]:
        """Produce a first-pass same-vs-new workflow decision between adjacent segments."""
        return [self.boundary_detector.decide(left, right) for left, right in zip(segments, segments[1:])]
