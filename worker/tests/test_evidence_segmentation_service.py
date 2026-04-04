from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import Mock

bootstrap_module = types.ModuleType("worker.bootstrap")


class _FakeSettings:
    ai_enabled = False
    ai_api_key = ""
    ai_base_url = ""
    ai_model = ""
    ai_timeout_seconds = 30


bootstrap_module.get_backend_settings = lambda: _FakeSettings()
sys.modules.setdefault("worker.bootstrap", bootstrap_module)

from worker.grouping.segmentation_service import (
    AISemanticEnrichmentStrategy,
    AIWorkflowBoundaryStrategy,
    HeuristicSemanticEnrichmentStrategy,
    HeuristicWorkflowBoundaryStrategy,
)
from worker.services.ai_transcript_interpreter import WorkflowBoundaryInterpretation, WorkflowSemanticEnrichmentInterpretation
from worker.services.workflow_intelligence import EvidenceSegment, WorkflowBoundaryDecision


class EvidenceSegmentationServiceTests(unittest.TestCase):
    def test_semantic_enrichment_extracts_richer_signals(self) -> None:
        strategy = HeuristicSemanticEnrichmentStrategy()
        segment = EvidenceSegment(
            id="seg-1",
            transcript_artifact_id="transcript-1",
            meeting_id=None,
            segment_order=1,
            text=(
                "The user opens SAP GUI and creates the sales order. "
                "The order data must be validated before save."
            ),
        )

        enrichment = strategy.enrich(segment)

        self.assertEqual(enrichment.actor, "User")
        self.assertEqual(enrichment.actor_role, "operator")
        self.assertEqual(enrichment.system_name, "SAP GUI".upper())
        self.assertEqual(enrichment.action_type, "navigate")
        self.assertEqual(enrichment.business_object, "Sales Order")
        self.assertIn("validated before save", " ".join(hint.lower() for hint in enrichment.rule_hints))
        self.assertIn("sales order", enrichment.domain_terms)
        self.assertIn(enrichment.confidence, {"medium", "high"})

    def test_boundary_detector_marks_new_workflow_when_object_changes(self) -> None:
        boundary_strategy = HeuristicWorkflowBoundaryStrategy()
        left = EvidenceSegment(
            id="left",
            transcript_artifact_id="transcript-1",
            meeting_id=None,
            segment_order=1,
            text="Create the purchase order in SAP.",
        )
        right = EvidenceSegment(
            id="right",
            transcript_artifact_id="transcript-2",
            meeting_id=None,
            segment_order=2,
            text="Now we will create the sales order in SAP.",
        )
        enricher = HeuristicSemanticEnrichmentStrategy()
        left.enrichment = enricher.enrich(left)
        right.enrichment = enricher.enrich(right)

        decision = boundary_strategy.decide(left, right)

        self.assertEqual(decision.decision, "new_workflow")
        self.assertIn("different business objects", decision.reason)

    def test_ai_enrichment_strategy_uses_ai_when_confident(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.enrich_workflow_segment.return_value = WorkflowSemanticEnrichmentInterpretation(
            actor="Lawyer",
            actor_role="reviewer",
            system_name="Harvey",
            action_verb="review",
            action_type="review",
            business_object="Commercial Contract",
            workflow_goal="Contract Review",
            rule_hints=["Review indemnity clauses before redlining"],
            domain_terms=["commercial contract", "redlining"],
            confidence="high",
            rationale="AI found strong legal review signals.",
        )
        strategy = AISemanticEnrichmentStrategy(ai_transcript_interpreter=ai_interpreter)
        segment = EvidenceSegment(
            id="seg-legal",
            transcript_artifact_id="transcript-1",
            meeting_id=None,
            segment_order=1,
            text="The lawyer uses Harvey to review commercial contracts and highlight indemnity clauses.",
        )

        enrichment = strategy.enrich(segment)

        self.assertEqual(enrichment.system_name, "Harvey")
        self.assertEqual(enrichment.business_object, "Commercial Contract")
        self.assertEqual(enrichment.workflow_goal, "Contract Review")
        self.assertEqual(enrichment.enrichment_source, "ai")

    def test_ai_enrichment_strategy_falls_back_when_ai_is_low_confidence(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.enrich_workflow_segment.return_value = WorkflowSemanticEnrichmentInterpretation(
            actor=None,
            actor_role=None,
            system_name=None,
            action_verb=None,
            action_type=None,
            business_object=None,
            workflow_goal=None,
            rule_hints=[],
            domain_terms=[],
            confidence="low",
            rationale="AI is unsure.",
        )
        strategy = AISemanticEnrichmentStrategy(ai_transcript_interpreter=ai_interpreter)
        segment = EvidenceSegment(
            id="seg-fallback",
            transcript_artifact_id="transcript-1",
            meeting_id=None,
            segment_order=1,
            text="The user opens SAP GUI and creates the sales order.",
        )

        enrichment = strategy.enrich(segment)

        self.assertEqual(enrichment.business_object, "Sales Order")
        self.assertEqual(enrichment.enrichment_source, "heuristic_fallback")

    def test_boundary_detector_keeps_same_workflow_when_signals_overlap(self) -> None:
        boundary_strategy = HeuristicWorkflowBoundaryStrategy()
        enricher = HeuristicSemanticEnrichmentStrategy()
        left = EvidenceSegment(
            id="left",
            transcript_artifact_id="transcript-1",
            meeting_id=None,
            segment_order=1,
            text="The user opens SAP and creates the purchase order header.",
            end_timestamp="00:00:12",
        )
        right = EvidenceSegment(
            id="right",
            transcript_artifact_id="transcript-1",
            meeting_id=None,
            segment_order=2,
            text="The user updates the purchase order item details in SAP.",
            start_timestamp="00:00:12",
        )
        left.enrichment = enricher.enrich(left)
        right.enrichment = enricher.enrich(right)

        decision = boundary_strategy.decide(left, right)

        self.assertEqual(decision.decision, "same_workflow")
        self.assertIn("shared object", decision.reason)

    def test_ai_boundary_strategy_uses_ai_when_confident(self) -> None:
        fallback_strategy = Mock()
        fallback_strategy.decide.return_value = WorkflowBoundaryDecision(
            left_segment_id="left",
            right_segment_id="right",
            decision="new_workflow",
            confidence="medium",
            reason="fallback",
        )
        ai_interpreter = Mock()
        ai_interpreter.classify_workflow_boundary.return_value = WorkflowBoundaryInterpretation(
            decision="same_workflow",
            confidence="high",
            rationale="AI found strong workflow continuity.",
        )
        strategy = AIWorkflowBoundaryStrategy(
            ai_transcript_interpreter=ai_interpreter,
            fallback_strategy=fallback_strategy,
        )
        enricher = HeuristicSemanticEnrichmentStrategy()
        left = EvidenceSegment(
            id="left",
            transcript_artifact_id="transcript-1",
            meeting_id=None,
            segment_order=1,
            text="Create the purchase order header in SAP.",
        )
        right = EvidenceSegment(
            id="right",
            transcript_artifact_id="transcript-1",
            meeting_id=None,
            segment_order=2,
            text="Update the purchase order line item in SAP.",
        )
        left.enrichment = enricher.enrich(left)
        right.enrichment = enricher.enrich(right)

        decision = strategy.decide(left, right)

        self.assertEqual(decision.decision, "same_workflow")
        self.assertEqual(decision.confidence, "high")
        self.assertIn("AI found strong workflow continuity", decision.reason)

    def test_ai_boundary_strategy_falls_back_when_ai_is_low_confidence(self) -> None:
        fallback_strategy = HeuristicWorkflowBoundaryStrategy()
        ai_interpreter = Mock()
        ai_interpreter.classify_workflow_boundary.return_value = WorkflowBoundaryInterpretation(
            decision="same_workflow",
            confidence="low",
            rationale="AI is not sure.",
        )
        strategy = AIWorkflowBoundaryStrategy(
            ai_transcript_interpreter=ai_interpreter,
            fallback_strategy=fallback_strategy,
        )
        enricher = HeuristicSemanticEnrichmentStrategy()
        left = EvidenceSegment(
            id="left",
            transcript_artifact_id="transcript-1",
            meeting_id=None,
            segment_order=1,
            text="Create the purchase order in SAP.",
        )
        right = EvidenceSegment(
            id="right",
            transcript_artifact_id="transcript-2",
            meeting_id=None,
            segment_order=2,
            text="Now we will create the sales order in SAP.",
        )
        left.enrichment = enricher.enrich(left)
        right.enrichment = enricher.enrich(right)

        decision = strategy.decide(left, right)

        self.assertEqual(decision.decision, "new_workflow")
        self.assertIn("different business objects", decision.reason)
        self.assertEqual(decision.decision_source, "heuristic_fallback")

    def test_ai_boundary_strategy_marks_conflict_unresolved_when_both_are_strong_and_disagree(self) -> None:
        fallback_strategy = Mock()
        fallback_strategy.decide.return_value = WorkflowBoundaryDecision(
            left_segment_id="left",
            right_segment_id="right",
            decision="same_workflow",
            confidence="high",
            reason="heuristic found strong continuity",
            decision_source="heuristic",
            heuristic_decision="same_workflow",
            heuristic_confidence="high",
        )
        ai_interpreter = Mock()
        ai_interpreter.classify_workflow_boundary.return_value = WorkflowBoundaryInterpretation(
            decision="new_workflow",
            confidence="high",
            rationale="AI found a materially different workflow objective.",
        )
        strategy = AIWorkflowBoundaryStrategy(
            ai_transcript_interpreter=ai_interpreter,
            fallback_strategy=fallback_strategy,
        )
        enricher = HeuristicSemanticEnrichmentStrategy()
        left = EvidenceSegment(
            id="left",
            transcript_artifact_id="transcript-1",
            meeting_id=None,
            segment_order=1,
            text="Create the purchase order in SAP.",
        )
        right = EvidenceSegment(
            id="right",
            transcript_artifact_id="transcript-2",
            meeting_id=None,
            segment_order=2,
            text="Create the sales order in SAP.",
        )
        left.enrichment = enricher.enrich(left)
        right.enrichment = enricher.enrich(right)

        decision = strategy.decide(left, right)

        self.assertEqual(decision.decision, "uncertain")
        self.assertEqual(decision.decision_source, "conflict_unresolved")
        self.assertTrue(decision.conflict_detected)


if __name__ == "__main__":
    unittest.main()
