from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from worker.services.process_grouping_service import ProcessGroupingService, TranscriptWorkflowProfile
from worker.services.ai_transcript_interpreter import (
    AmbiguousProcessGroupResolution,
    WorkflowGroupMatchInterpretation,
    WorkflowTitleInterpretation,
)


class ProcessGroupingServiceTests(unittest.TestCase):
    def test_resolve_title_with_ai_prefers_ai_title_when_confident(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.resolve_workflow_title.return_value = WorkflowTitleInterpretation(
            workflow_title="Sales Order Creation",
            canonical_slug="sales-order-creation",
            confidence="high",
            rationale="AI normalized the workflow title to the business process name.",
        )
        service = ProcessGroupingService(ai_transcript_interpreter=ai_interpreter)
        transcript = SimpleNamespace(id="transcript-1", name="sales-order.txt")
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["User"],
            top_objects=["Sales Order"],
            top_systems=["SAP"],
            top_actions=["open"],
            top_goals=["Open Sales Order"],
            top_rules=[],
        )

        title = service._resolve_title_with_ai(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Open sales order in SAP"}],
            workflow_profile=profile,
            fallback_title="Open Sales Order",
        )

        self.assertEqual(title.workflow_title, "Sales Order Creation")
        self.assertEqual(title.canonical_slug, "sales-order-creation")

    def test_resolve_title_with_ai_falls_back_when_ai_is_low_confidence(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.resolve_workflow_title.return_value = WorkflowTitleInterpretation(
            workflow_title="Sales Workflow",
            canonical_slug="sales-workflow",
            confidence="low",
            rationale="AI is not sure.",
        )
        service = ProcessGroupingService(ai_transcript_interpreter=ai_interpreter)
        transcript = SimpleNamespace(id="transcript-1", name="sales-order.txt")
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["User"],
            top_objects=["Sales Order"],
            top_systems=["SAP"],
            top_actions=["open"],
            top_goals=["Open Sales Order"],
            top_rules=[],
        )

        title = service._resolve_title_with_ai(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Open sales order in SAP"}],
            workflow_profile=profile,
            fallback_title="Sales Order Creation",
        )

        self.assertEqual(title.workflow_title, "Sales Order Creation")

    def test_fallback_title_normalizes_open_sales_order_to_business_title(self) -> None:
        service = ProcessGroupingService()
        transcript = SimpleNamespace(id="transcript-1", name="sales-order.txt")
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["User"],
            top_objects=["Sales Order"],
            top_systems=["SAP"],
            top_actions=["open"],
            top_goals=["Open Sales Order"],
            top_rules=[],
        )

        title = service._fallback_title(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Create sales order in SAP"}],
            workflow_profile=profile,
        )

        self.assertEqual(title, "Sales Order Creation")

    def test_fallback_title_normalizes_go_to_purchase_order_to_business_title(self) -> None:
        service = ProcessGroupingService()
        transcript = SimpleNamespace(id="transcript-2", name="purchase-order.txt")
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-2",
            top_actors=["User"],
            top_objects=["Purchase Order"],
            top_systems=["SAP"],
            top_actions=["go to"],
            top_goals=["Go To Purchase Order"],
            top_rules=[],
        )

        title = service._fallback_title(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Create purchase order in SAP"}],
            workflow_profile=profile,
        )

        self.assertEqual(title, "Purchase Order Creation")

    def test_match_existing_group_marks_ambiguity_for_close_candidates(self) -> None:
        service = ProcessGroupingService()
        workflow_profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["User"],
            top_objects=["Sales Order"],
            top_systems=["SAP"],
            top_actions=["create"],
            top_goals=["Create Sales Order"],
            top_rules=["validate order data"],
        )
        steps = [
            {
                "action_text": "Create sales order and validate order data in SAP",
            }
        ]
        existing_groups = [
            SimpleNamespace(
                title="Sales Order Creation",
                canonical_slug="sales-order-creation",
                summary_text="Create sales order validate order data SAP",
            ),
            SimpleNamespace(
                title="Sales Order Processing",
                canonical_slug="sales-order-processing",
                summary_text="Create sales order process order data SAP validate controls",
            ),
        ]

        result = service._match_existing_group(  # noqa: SLF001
            slug="sales-order-operations",
            title="Sales Order Operations",
            steps=steps,
            workflow_profile=workflow_profile,
            existing_groups=existing_groups,
        )

        self.assertTrue(result["ambiguity"])
        self.assertGreaterEqual(len(result["candidate_matches"]), 2)
        self.assertIn("competing_group_candidates", result["supporting_signals"])

    def test_resolve_group_identity_uses_ai_for_ambiguous_existing_match(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.resolve_ambiguous_process_group.return_value = AmbiguousProcessGroupResolution(
            matched_existing_title="Sales Order Creation",
            recommended_title="Sales Order Creation",
            recommended_slug="sales-order-creation",
            confidence="high",
            rationale="AI confirmed the transcript belongs to the existing sales order creation workflow.",
        )
        service = ProcessGroupingService(ai_transcript_interpreter=ai_interpreter)
        transcript = SimpleNamespace(id="transcript-1", name="sales-order.txt")
        existing_group = SimpleNamespace(
            title="Sales Order Creation",
            canonical_slug="sales-order-creation",
            summary_text="Create sales order validate order data SAP",
        )
        competing_group = SimpleNamespace(
            title="Sales Order Processing",
            canonical_slug="sales-order-processing",
            summary_text="Create sales order process order data SAP validate controls",
        )
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["User"],
            top_objects=["Sales Order"],
            top_systems=["SAP"],
            top_actions=["create"],
            top_goals=["Create Sales Order"],
            top_rules=["validate order data"],
        )
        service._match_existing_group = Mock(  # type: ignore[method-assign]
            return_value={
                "matched_group": existing_group,
                "best_score": 0.84,
                "ambiguity": True,
                "candidate_matches": [
                    {"group_title": existing_group.title, "score": 0.84},
                    {"group_title": competing_group.title, "score": 0.79},
                ],
                "supporting_signals": ["strong_existing_group_match", "competing_group_candidates"],
            }
        )

        decision = service._resolve_group_identity(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Create sales order and validate order data in SAP"}],
            notes=[],
            existing_groups=[existing_group, competing_group],
            workflow_profile=profile,
            previous_workflow_profile=None,
            previous_group=None,
        )

        self.assertEqual(decision.decision, "ai_resolved_ambiguous_match")
        self.assertFalse(decision.is_ambiguous)
        self.assertEqual(decision.matched_group, existing_group)
        ai_interpreter.resolve_ambiguous_process_group.assert_called_once()

    def test_resolve_group_identity_uses_ai_for_ambiguous_new_group(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.resolve_ambiguous_process_group.return_value = AmbiguousProcessGroupResolution(
            matched_existing_title=None,
            recommended_title="Returns Order Processing",
            recommended_slug="returns-order-processing",
            confidence="medium",
            rationale="AI determined the transcript is materially different from the existing workflows.",
        )
        service = ProcessGroupingService(ai_transcript_interpreter=ai_interpreter)
        transcript = SimpleNamespace(id="transcript-2", name="returns-order.txt")
        existing_group = SimpleNamespace(
            title="Sales Order Creation",
            canonical_slug="sales-order-creation",
            summary_text="Create sales order validate order data SAP",
        )
        competing_group = SimpleNamespace(
            title="Sales Order Processing",
            canonical_slug="sales-order-processing",
            summary_text="Create sales order process order data SAP validate controls",
        )
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-2",
            top_actors=["User"],
            top_objects=["Sales Order"],
            top_systems=["SAP"],
            top_actions=["create"],
            top_goals=["Create Sales Order"],
            top_rules=["validate order data"],
        )
        service._match_existing_group = Mock(  # type: ignore[method-assign]
            return_value={
                "matched_group": None,
                "best_score": 0.78,
                "ambiguity": True,
                "candidate_matches": [
                    {"group_title": existing_group.title, "score": 0.78},
                    {"group_title": competing_group.title, "score": 0.74},
                ],
                "supporting_signals": ["moderate_existing_group_match", "competing_group_candidates"],
            }
        )

        decision = service._resolve_group_identity(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Create sales order and validate order data in SAP"}],
            notes=[],
            existing_groups=[existing_group, competing_group],
            workflow_profile=profile,
            previous_workflow_profile=None,
            previous_group=None,
        )

        self.assertEqual(decision.decision, "ai_resolved_ambiguous_new_group")
        self.assertFalse(decision.is_ambiguous)
        self.assertIsNone(decision.matched_group)
        self.assertEqual(decision.inferred_title, "Returns Order Processing")
        ai_interpreter.resolve_ambiguous_process_group.assert_called_once()

    def test_resolve_group_identity_uses_ai_group_matcher_when_confident(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.resolve_workflow_title.return_value = WorkflowTitleInterpretation(
            workflow_title="Sales Order Creation",
            canonical_slug="sales-order-creation",
            confidence="high",
            rationale="AI normalized the title.",
        )
        ai_interpreter.match_existing_workflow_group.return_value = WorkflowGroupMatchInterpretation(
            matched_existing_title="Sales Order Creation",
            recommended_title="Sales Order Creation",
            recommended_slug="sales-order-creation",
            confidence="high",
            rationale="AI determined the transcript matches the existing sales order workflow.",
        )
        service = ProcessGroupingService(ai_transcript_interpreter=ai_interpreter)
        transcript = SimpleNamespace(id="transcript-1", name="sales-order.txt")
        existing_group = SimpleNamespace(
            title="Sales Order Creation",
            canonical_slug="sales-order-creation",
            summary_text="Create sales order validate order data SAP",
        )
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["User"],
            top_objects=["Sales Order"],
            top_systems=["SAP"],
            top_actions=["create"],
            top_goals=["Create Sales Order"],
            top_rules=["validate order data"],
        )

        decision = service._resolve_group_identity(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Create sales order and validate order data in SAP"}],
            notes=[],
            existing_groups=[existing_group],
            workflow_profile=profile,
            previous_workflow_profile=None,
            previous_group=None,
        )

        self.assertEqual(decision.decision, "ai_matched_existing_group")
        self.assertEqual(decision.matched_group, existing_group)
        ai_interpreter.match_existing_workflow_group.assert_called_once()

    def test_resolve_group_identity_falls_back_to_heuristics_when_ai_group_match_is_weak(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.resolve_workflow_title.return_value = WorkflowTitleInterpretation(
            workflow_title="Sales Order Creation",
            canonical_slug="sales-order-creation",
            confidence="high",
            rationale="AI normalized the title.",
        )
        ai_interpreter.match_existing_workflow_group.return_value = WorkflowGroupMatchInterpretation(
            matched_existing_title="Sales Order Processing",
            recommended_title="Sales Order Processing",
            recommended_slug="sales-order-processing",
            confidence="low",
            rationale="AI is not sure.",
        )
        service = ProcessGroupingService(ai_transcript_interpreter=ai_interpreter)
        transcript = SimpleNamespace(id="transcript-1", name="sales-order.txt")
        existing_group = SimpleNamespace(
            title="Sales Order Creation",
            canonical_slug="sales-order-creation",
            summary_text="Create sales order validate order data SAP",
        )
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["User"],
            top_objects=["Sales Order"],
            top_systems=["SAP"],
            top_actions=["create"],
            top_goals=["Create Sales Order"],
            top_rules=["validate order data"],
        )

        decision = service._resolve_group_identity(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Create sales order and validate order data in SAP"}],
            notes=[],
            existing_groups=[existing_group],
            workflow_profile=profile,
            previous_workflow_profile=None,
            previous_group=None,
        )

        self.assertEqual(decision.decision, "matched_existing_group")
        self.assertEqual(decision.matched_group, existing_group)


if __name__ == "__main__":
    unittest.main()
