from __future__ import annotations

import logging

from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
from worker.ai_skills.workflow_boundary_detection.schemas import WorkflowBoundaryDetectionRequest
from worker.ai_skills.workflow_boundary_detection.skill import WorkflowBoundaryDetectionSkill
from worker.services.workflow_intelligence import EvidenceSegment, WorkflowBoundaryDecision
from worker.grouping.segmentation_boundary_heuristics import HeuristicWorkflowBoundaryStrategy
from worker.grouping.segmentation_interpreter_adapters import InterpreterWorkflowBoundarySkill

logger = logging.getLogger(__name__)


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

    def _resolve_conflict(self, *, left: EvidenceSegment, right: EvidenceSegment, heuristic_decision: WorkflowBoundaryDecision, ai_decision) -> WorkflowBoundaryDecision:
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
            "enrichment": None if enrichment is None else {
                "actor": enrichment.actor,
                "actor_role": enrichment.actor_role,
                "system_name": enrichment.system_name,
                "action_verb": enrichment.action_verb,
                "action_type": enrichment.action_type,
                "business_object": enrichment.business_object,
                "workflow_goal": enrichment.workflow_goal,
                "rule_hints": enrichment.rule_hints,
                "domain_terms": enrichment.domain_terms,
                "confidence": enrichment.confidence,
            },
        }
