from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from worker.services.ai_transcript.interpreter import AITranscriptInterpreter
from worker.services.ai_skills.semantic_enrichment.schemas import SemanticEnrichmentRequest
from worker.services.ai_skills.semantic_enrichment.skill import SemanticEnrichmentSkill
from worker.services.ai_skills.workflow_boundary_detection.schemas import WorkflowBoundaryDetectionRequest
from worker.services.ai_skills.workflow_boundary_detection.skill import WorkflowBoundaryDetectionSkill
from worker.services.workflow_intelligence import EvidenceSegment, SemanticEnrichment, WorkflowBoundaryDecision
from worker.services.workflow_intelligence.segmentation_ai_adapters import (
    InterpreterSemanticEnrichmentSkill,
    InterpreterWorkflowBoundarySkill,
)
from worker.services.workflow_intelligence.segmentation_heuristics import (
    HeuristicSemanticEnrichmentStrategy,
    HeuristicWorkflowBoundaryStrategy,
)

if TYPE_CHECKING:
    from worker.services.ai_transcript.interpreter import WorkflowBoundaryInterpretation

logger = logging.getLogger(__name__)


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
            InterpreterSemanticEnrichmentSkill(self.ai_transcript_interpreter)
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
            InterpreterWorkflowBoundarySkill(self.ai_transcript_interpreter)
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
        ai_decision: WorkflowBoundaryInterpretation,
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
