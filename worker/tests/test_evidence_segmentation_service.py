from __future__ import annotations

import unittest

from worker.services.evidence_segmentation_service import (
    HeuristicSemanticEnrichmentStrategy,
    HeuristicWorkflowBoundaryStrategy,
)
from worker.services.workflow_intelligence import EvidenceSegment


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


if __name__ == "__main__":
    unittest.main()
