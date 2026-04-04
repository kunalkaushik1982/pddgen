from __future__ import annotations

from . import EvidenceSegment, WorkflowBoundaryDecision


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
            reasons.append("timestamp continuity")
        if overlap_score >= 0.35:
            return WorkflowBoundaryDecision(
                left_segment_id=left.id,
                right_segment_id=right.id,
                decision="same_workflow",
                confidence="high" if overlap_score >= 0.6 else "medium",
                reason=", ".join(reasons) if reasons else "Shared workflow signals suggested continuity.",
                decision_source="heuristic",
                heuristic_decision="same_workflow",
                heuristic_confidence="high" if overlap_score >= 0.6 else "medium",
            )
        if overlap_score <= -0.1:
            return WorkflowBoundaryDecision(
                left_segment_id=left.id,
                right_segment_id=right.id,
                decision="new_workflow",
                confidence="high" if overlap_score <= -0.35 else "medium",
                reason=", ".join(reasons) if reasons else "Conflicting workflow signals suggested a new workflow boundary.",
                decision_source="heuristic",
                heuristic_decision="new_workflow",
                heuristic_confidence="high" if overlap_score <= -0.35 else "medium",
            )
        return WorkflowBoundaryDecision(
            left_segment_id=left.id,
            right_segment_id=right.id,
            decision="uncertain",
            confidence="low",
            reason=", ".join(reasons) if reasons else "Signals were insufficient to determine a boundary confidently.",
            decision_source="heuristic",
            heuristic_decision="uncertain",
            heuristic_confidence="low",
        )

    @staticmethod
    def _has_explicit_new_workflow_marker(text: str) -> bool:
        lowered = text.lower()
        return any(marker in lowered for marker in ("next process", "another workflow", "different workflow", "new workflow"))

    @staticmethod
    def _is_timestamp_contiguous(left: EvidenceSegment, right: EvidenceSegment) -> bool:
        return bool(left.end_timestamp and right.start_timestamp and left.end_timestamp <= right.start_timestamp)
