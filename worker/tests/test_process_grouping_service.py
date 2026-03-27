from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from worker.services.process_grouping_service import ProcessGroupingService, TranscriptWorkflowProfile
from worker.services.ai_transcript_interpreter import (
    AITranscriptInterpreter,
    AmbiguousProcessGroupResolution,
    ProcessSummaryInterpretation,
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

    def test_resolve_title_with_ai_normalizes_ui_style_ai_title(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.resolve_workflow_title.return_value = WorkflowTitleInterpretation(
            workflow_title="Open Sales Order",
            canonical_slug="open-sales-order",
            confidence="high",
            rationale="AI proposed a title from the workflow evidence.",
        )
        service = ProcessGroupingService(ai_transcript_interpreter=ai_interpreter)
        transcript = SimpleNamespace(id="transcript-1", name="sales-order.txt")
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["User"],
            top_objects=["Sales Order"],
            top_systems=["SAP"],
            top_actions=["create"],
            top_goals=["Create Sales Order"],
            top_rules=[],
        )

        title = service._resolve_title_with_ai(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Create sales order in SAP"}],
            workflow_profile=profile,
            fallback_title="Sales Order Creation",
        )

        self.assertEqual(title.workflow_title, "Sales Order Creation")

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

    def test_match_existing_group_penalizes_application_mismatch(self) -> None:
        service = ProcessGroupingService()
        workflow_profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["Lawyer"],
            top_objects=["Contract"],
            top_systems=["Harvey"],
            top_applications=["Harvey Workspace"],
            top_actions=["review"],
            top_goals=["Review contract obligations"],
            top_rules=["flag legal issues"],
        )
        steps = [
            {
                "application_name": "Harvey Workspace",
                "action_text": "Review contract clauses and create redlines",
            }
        ]
        existing_groups = [
            SimpleNamespace(
                title="CoCounsel Contract Review",
                canonical_slug="cocounsel-contract-review",
                summary_text="Review contracts in CoCounsel workspace and generate legal issue reports",
            )
        ]

        result = service._match_existing_group(  # noqa: SLF001
            slug="contract-review",
            title="Contract Review Workflow",
            steps=steps,
            workflow_profile=workflow_profile,
            existing_groups=existing_groups,
        )

        self.assertIsNone(result["matched_group"])
        self.assertLess(float(result["candidate_matches"][0]["application_alignment"]), 0)

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

    def test_resolve_group_identity_allows_high_confidence_ai_to_override_weaker_heuristic_grouping(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.resolve_workflow_title.return_value = WorkflowTitleInterpretation(
            workflow_title="Contract Review Workflow",
            canonical_slug="contract-review-workflow",
            confidence="high",
            rationale="AI normalized the title.",
        )
        ai_interpreter.match_existing_workflow_group.return_value = WorkflowGroupMatchInterpretation(
            matched_existing_title="Harvey Contract Review",
            recommended_title="Harvey Contract Review",
            recommended_slug="harvey-contract-review",
            confidence="high",
            rationale="AI found the operational sequence aligned to Harvey.",
        )
        service = ProcessGroupingService(ai_transcript_interpreter=ai_interpreter)
        transcript = SimpleNamespace(id="transcript-1", name="contract-review.txt")
        weaker_group = SimpleNamespace(
            title="Legal Document Analysis",
            canonical_slug="legal-document-analysis",
            summary_text="Review legal documents using mixed tools",
        )
        ai_group = SimpleNamespace(
            title="Harvey Contract Review",
            canonical_slug="harvey-contract-review",
            summary_text="Review contracts inside Harvey and generate legal analysis outputs",
        )
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["Lawyer"],
            top_objects=["Contract"],
            top_systems=["Harvey"],
            top_actions=["review"],
            top_goals=["Review contract obligations"],
            top_rules=["flag legal issues"],
        )
        service._match_existing_group = Mock(  # type: ignore[method-assign]
            return_value={
                "matched_group": weaker_group,
                "best_score": 0.81,
                "ambiguity": False,
                "candidate_matches": [{"group_title": weaker_group.title, "score": 0.81}],
                "supporting_signals": ["moderate_existing_group_match"],
            }
        )

        decision = service._resolve_group_identity(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Review contract clauses in Harvey"}],
            notes=[],
            existing_groups=[weaker_group, ai_group],
            workflow_profile=profile,
            previous_workflow_profile=None,
            previous_group=None,
        )

        self.assertEqual(decision.decision_source, "ai_conflict_override")
        self.assertEqual(decision.matched_group, ai_group)
        self.assertTrue(decision.conflict_detected)
        self.assertEqual(decision.heuristic_decision, "matched_existing_group")
        self.assertEqual(decision.ai_decision, "matched_existing_group")

    def test_resolve_group_identity_keeps_high_confidence_heuristic_when_ai_conflicts_weakly(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.resolve_workflow_title.return_value = WorkflowTitleInterpretation(
            workflow_title="Harvey Contract Review",
            canonical_slug="harvey-contract-review",
            confidence="high",
            rationale="AI normalized the title.",
        )
        ai_interpreter.match_existing_workflow_group.return_value = WorkflowGroupMatchInterpretation(
            matched_existing_title=None,
            recommended_title="Independent Legal Workflow",
            recommended_slug="independent-legal-workflow",
            confidence="medium",
            rationale="AI was not fully sure this should attach to an existing workflow.",
        )
        service = ProcessGroupingService(ai_transcript_interpreter=ai_interpreter)
        transcript = SimpleNamespace(id="transcript-1", name="harvey-review.txt")
        existing_group = SimpleNamespace(
            title="Harvey Contract Review",
            canonical_slug="harvey-contract-review",
            summary_text="Review contracts inside Harvey and generate legal analysis outputs",
        )
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["Lawyer"],
            top_objects=["Contract"],
            top_systems=["Harvey"],
            top_actions=["review"],
            top_goals=["Review contract obligations"],
            top_rules=["flag legal issues"],
        )
        service._match_existing_group = Mock(  # type: ignore[method-assign]
            return_value={
                "matched_group": existing_group,
                "best_score": 0.95,
                "ambiguity": False,
                "candidate_matches": [{"group_title": existing_group.title, "score": 0.95}],
                "supporting_signals": ["strong_existing_group_match"],
            }
        )

        decision = service._resolve_group_identity(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Review contract clauses in Harvey"}],
            notes=[],
            existing_groups=[existing_group],
            workflow_profile=profile,
            previous_workflow_profile=None,
            previous_group=None,
        )

        self.assertEqual(decision.decision_source, "heuristic_fallback")
        self.assertEqual(decision.matched_group, existing_group)
        self.assertTrue(decision.conflict_detected)
        self.assertEqual(decision.ai_decision, "created_new_group")
        self.assertEqual(decision.heuristic_confidence, "high")

    def test_resolve_group_identity_marks_unresolved_conflict_as_ambiguous(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.resolve_workflow_title.return_value = WorkflowTitleInterpretation(
            workflow_title="Legal Workflow",
            canonical_slug="legal-workflow",
            confidence="high",
            rationale="AI normalized the title.",
        )
        ai_interpreter.match_existing_workflow_group.return_value = WorkflowGroupMatchInterpretation(
            matched_existing_title=None,
            recommended_title="Independent Legal Workflow",
            recommended_slug="independent-legal-workflow",
            confidence="medium",
            rationale="AI saw enough operational differences to suggest a new workflow.",
        )
        service = ProcessGroupingService(ai_transcript_interpreter=ai_interpreter)
        transcript = SimpleNamespace(id="transcript-1", name="legal-workflow.txt")
        existing_group = SimpleNamespace(
            title="Harvey Contract Review",
            canonical_slug="harvey-contract-review",
            summary_text="Review contracts inside Harvey and generate legal analysis outputs",
        )
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["Lawyer"],
            top_objects=["Contract"],
            top_systems=["Harvey"],
            top_actions=["review"],
            top_goals=["Review contract obligations"],
            top_rules=["flag legal issues"],
        )
        service._match_existing_group = Mock(  # type: ignore[method-assign]
            return_value={
                "matched_group": existing_group,
                "best_score": 0.84,
                "ambiguity": False,
                "candidate_matches": [{"group_title": existing_group.title, "score": 0.84}],
                "supporting_signals": ["moderate_existing_group_match"],
            }
        )

        decision = service._resolve_group_identity(  # noqa: SLF001
            transcript=transcript,
            steps=[{"action_text": "Review contract clauses in Harvey"}],
            notes=[],
            existing_groups=[existing_group],
            workflow_profile=profile,
            previous_workflow_profile=None,
            previous_group=None,
        )

        self.assertEqual(decision.decision_source, "conflict_unresolved")
        self.assertTrue(decision.is_ambiguous)
        self.assertTrue(decision.conflict_detected)
        self.assertEqual(decision.decision, "ambiguously_matched_existing_group")

    def test_normalize_capability_tags_deduplicates_and_excludes_process_title(self) -> None:
        service = ProcessGroupingService()

        normalized = service._normalize_capability_tags(  # noqa: SLF001
            ["Contract Review", "contract review", "Harvey Contract Review", "Legal Analysis"],
            process_title="Harvey Contract Review",
        )

        self.assertEqual(normalized, ["Contract Review", "Legal Analysis"])

    def test_ai_confidence_calibration_downgrades_when_evidence_is_thin(self) -> None:
        calibrated = AITranscriptInterpreter._calibrate_confidence(  # noqa: SLF001
            "high",
            evidence_points=1,
            quality_points=1,
        )

        self.assertEqual(calibrated, "low")

    def test_build_transcript_profiles_collects_application_names_from_steps(self) -> None:
        profiles = ProcessGroupingService._build_transcript_profiles(  # noqa: SLF001
            evidence_segments=[],
            workflow_boundary_decisions=[],
            steps_by_transcript={
                "transcript-1": [
                    {"application_name": "Harvey Workspace", "action_text": "Review clauses"},
                    {"application_name": "Harvey Workspace", "action_text": "Generate report"},
                    {"application_name": "Microsoft Word", "action_text": "Edit redlines"},
                ]
            },
        )

        self.assertEqual(profiles["transcript-1"].top_applications, ["Harvey Workspace", "Microsoft Word"])

    def test_match_existing_group_prefers_application_aligned_candidate_for_same_domain(self) -> None:
        service = ProcessGroupingService()
        workflow_profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["Lawyer"],
            top_objects=["Contract"],
            top_systems=["Harvey"],
            top_applications=["Harvey Workspace"],
            top_actions=["review"],
            top_goals=["Review contract obligations"],
            top_rules=["flag legal issues"],
            top_domain_terms=["legal analysis", "contract review"],
        )
        steps = [
            {
                "application_name": "Harvey Workspace",
                "action_text": "Review contract clauses and generate legal analysis in Harvey Workspace",
            }
        ]
        existing_groups = [
            SimpleNamespace(
                title="General Legal Analysis",
                canonical_slug="general-legal-analysis",
                summary_text="Review contracts and legal documents across mixed tools for legal analysis",
            ),
            SimpleNamespace(
                title="Harvey Contract Review",
                canonical_slug="harvey-contract-review",
                summary_text="Review contracts in Harvey Workspace and generate legal analysis reports for lawyers",
            ),
        ]

        result = service._match_existing_group(  # noqa: SLF001
            slug="contract-review",
            title="Contract Review Workflow",
            steps=steps,
            workflow_profile=workflow_profile,
            existing_groups=existing_groups,
        )

        self.assertEqual(result["matched_group"], existing_groups[1])
        self.assertGreater(
            float(result["candidate_matches"][0]["application_alignment"]),
            float(result["candidate_matches"][1]["application_alignment"]),
        )

    def test_refresh_group_summaries_uses_ai_summary_when_confident(self) -> None:
        ai_interpreter = Mock()
        ai_interpreter.summarize_process_group.return_value = ProcessSummaryInterpretation(
            summary_text="This workflow creates a sales order in SAP and validates the customer and line-item details before saving the order.",
            confidence="high",
            rationale="AI found a clear sales order workflow.",
        )
        service = ProcessGroupingService(ai_transcript_interpreter=ai_interpreter)
        process_group = SimpleNamespace(id="group-1", title="Sales Order Creation", summary_text="")
        workflow_profile = TranscriptWorkflowProfile(
            transcript_artifact_id="transcript-1",
            top_actors=["User"],
            top_objects=["Sales Order"],
            top_systems=["SAP"],
            top_actions=["create"],
            top_goals=["Sales Order Creation"],
            top_rules=["validate customer details"],
        )

        service._refresh_group_summaries(  # noqa: SLF001
            process_groups=[process_group],
            transcript_group_ids={"transcript-1": "group-1"},
            steps_by_transcript={
                "transcript-1": [
                    {"action_text": "Enter sold-to party and material number", "supporting_transcript_text": "Enter sold-to party and material number"}
                ]
            },
            notes_by_transcript={"transcript-1": [{"text": "Validate order completeness"}]},
            workflow_profiles={"transcript-1": workflow_profile},
            document_type="pdd",
        )

        self.assertIn("sales order", process_group.summary_text.lower())
        ai_interpreter.summarize_process_group.assert_called_once()


if __name__ == "__main__":
    unittest.main()
