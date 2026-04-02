from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

SCHEMAS_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "workflow_boundary_detection"
    / "schemas.py"
)
SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "workflow_boundary_detection"
    / "skill.py"
)
CLIENT_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "client.py"
RUNTIME_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "runtime.py"
WORKFLOW_INTELLIGENCE_PATH = Path(__file__).resolve().parents[1] / "services" / "workflow_intelligence.py"
EVIDENCE_SEGMENTATION_PATH = Path(__file__).resolve().parents[1] / "services" / "evidence_segmentation_service.py"
SEMANTIC_SCHEMAS_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "semantic_enrichment"
    / "schemas.py"
)
SEMANTIC_SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "semantic_enrichment"
    / "skill.py"
)


def load_schemas_module():
    spec = importlib.util.spec_from_file_location("workflow_boundary_detection_schemas", SCHEMAS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_skill_module():
    spec = importlib.util.spec_from_file_location("workflow_boundary_detection_skill", SKILL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_client_module():
    spec = importlib.util.spec_from_file_location("ai_skill_client_boundary", CLIENT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_runtime_module():
    spec = importlib.util.spec_from_file_location("ai_skill_runtime_boundary", RUNTIME_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_workflow_intelligence_module():
    spec = importlib.util.spec_from_file_location("workflow_intelligence_boundary", WORKFLOW_INTELLIGENCE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_semantic_schemas_module():
    spec = importlib.util.spec_from_file_location("semantic_enrichment_schemas_boundary", SEMANTIC_SCHEMAS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_semantic_skill_module():
    spec = importlib.util.spec_from_file_location("semantic_enrichment_skill_boundary", SEMANTIC_SKILL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_evidence_segmentation_module():
    worker_module = types.ModuleType("worker")
    worker_module.__path__ = []  # type: ignore[attr-defined]
    services_module = types.ModuleType("worker.services")
    services_module.__path__ = []  # type: ignore[attr-defined]
    ai_skills_module = types.ModuleType("worker.services.ai_skills")
    ai_skills_module.__path__ = []  # type: ignore[attr-defined]
    semantic_module = types.ModuleType("worker.services.ai_skills.semantic_enrichment")
    semantic_module.__path__ = []  # type: ignore[attr-defined]
    boundary_module = types.ModuleType("worker.services.ai_skills.workflow_boundary_detection")
    boundary_module.__path__ = []  # type: ignore[attr-defined]

    ai_transcript_module = types.ModuleType("worker.services.ai_transcript_interpreter")

    class FakeInterpreter:
        def classify_workflow_boundary(self, **kwargs):
            return None

        def enrich_workflow_segment(self, **kwargs):
            return None

    ai_transcript_module.AITranscriptInterpreter = FakeInterpreter

    draft_support_module = types.ModuleType("worker.services.draft_generation_support")
    draft_support_module.ACTION_VERB_PATTERNS = {"review": ("review",), "create": ("create",)}
    draft_support_module.TIMESTAMP_PATTERN = None
    draft_support_module.classify_action_type = lambda text: "review"

    strategy_interfaces_module = types.ModuleType("worker.services.workflow_strategy_interfaces")
    strategy_interfaces_module.WorkflowIntelligenceStrategySet = object

    workflow_intelligence_module = load_workflow_intelligence_module()

    sys.modules["worker"] = worker_module
    sys.modules["worker.services"] = services_module
    sys.modules["worker.services.ai_skills"] = ai_skills_module
    sys.modules["worker.services.ai_skills.semantic_enrichment"] = semantic_module
    sys.modules["worker.services.ai_skills.workflow_boundary_detection"] = boundary_module
    sys.modules["worker.services.ai_transcript_interpreter"] = ai_transcript_module
    sys.modules["worker.services.ai_skills.client"] = load_client_module()
    sys.modules["worker.services.ai_skills.runtime"] = load_runtime_module()
    sys.modules["worker.services.ai_skills.semantic_enrichment.schemas"] = load_semantic_schemas_module()
    sys.modules["worker.services.ai_skills.semantic_enrichment.skill"] = load_semantic_skill_module()
    sys.modules["worker.services.ai_skills.workflow_boundary_detection.schemas"] = load_schemas_module()
    sys.modules["worker.services.ai_skills.workflow_boundary_detection.skill"] = load_skill_module()
    sys.modules["worker.services.draft_generation_support"] = draft_support_module
    sys.modules["worker.services.workflow_strategy_interfaces"] = strategy_interfaces_module
    sys.modules["worker.services.workflow_intelligence"] = workflow_intelligence_module

    spec = importlib.util.spec_from_file_location("evidence_segmentation_boundary", EVIDENCE_SEGMENTATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, workflow_intelligence_module


class WorkflowBoundaryDetectionSchemaTests(unittest.TestCase):
    def test_boundary_request_keeps_left_and_right_segments(self) -> None:
        schemas = load_schemas_module()
        request = schemas.WorkflowBoundaryDetectionRequest(
            left_segment={"id": "left-1", "text": "Open SAP"},
            right_segment={"id": "right-1", "text": "Review vendor"},
        )

        self.assertEqual(request.left_segment["id"], "left-1")
        self.assertEqual(request.right_segment["id"], "right-1")

    def test_boundary_response_keeps_decision_and_confidence(self) -> None:
        schemas = load_schemas_module()
        response = schemas.WorkflowBoundaryDetectionResponse(
            decision="same_workflow",
            confidence="high",
            rationale="Shared object and system",
        )

        self.assertEqual(response.decision, "same_workflow")
        self.assertEqual(response.confidence, "high")

    def test_normalize_decision_limits_values(self) -> None:
        skill = load_skill_module()

        self.assertEqual(skill.normalize_decision("same_workflow"), "same_workflow")
        self.assertEqual(skill.normalize_decision("bad"), "uncertain")

    def test_build_messages_includes_both_segments(self) -> None:
        schemas = load_schemas_module()
        skill_module = load_skill_module()
        request = schemas.WorkflowBoundaryDetectionRequest(
            left_segment={"id": "left-1", "text": "Open SAP"},
            right_segment={"id": "right-1", "text": "Review vendor"},
        )

        skill = skill_module.WorkflowBoundaryDetectionSkill(client=object())
        messages = skill.build_messages(request)

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("same business workflow", messages[0]["content"])
        self.assertIn("Open SAP", messages[1]["content"])
        self.assertIn("Review vendor", messages[1]["content"])

    def test_ai_boundary_strategy_uses_skill_and_preserves_decision_shape(self) -> None:
        evidence_module, workflow_module = load_evidence_segmentation_module()

        class StubBoundarySkill:
            skill_id = "workflow_boundary_detection"
            version = "1.0"

            def run(self, input: object):
                schemas = load_schemas_module()
                return schemas.WorkflowBoundaryDetectionResponse(
                    decision="same_workflow",
                    confidence="high",
                    rationale="Shared object and system",
                )

        strategy = evidence_module.AIWorkflowBoundaryStrategy()
        strategy._workflow_boundary_skill = StubBoundarySkill()
        left = workflow_module.EvidenceSegment(
            id="left-1",
            transcript_artifact_id="artifact-1",
            meeting_id=None,
            segment_order=1,
            text="Open SAP vendor record",
            enrichment=workflow_module.SemanticEnrichment(
                system_name="SAP",
                business_object="Vendor",
                workflow_goal="Review Vendor",
                action_type="review",
                domain_terms=["vendor", "review"],
                confidence="high",
            ),
        )
        right = workflow_module.EvidenceSegment(
            id="right-1",
            transcript_artifact_id="artifact-1",
            meeting_id=None,
            segment_order=2,
            text="Review vendor details",
            enrichment=workflow_module.SemanticEnrichment(
                system_name="SAP",
                business_object="Vendor",
                workflow_goal="Review Vendor",
                action_type="review",
                domain_terms=["vendor", "review"],
                confidence="high",
            ),
        )

        result = strategy.decide(left, right)

        self.assertIsInstance(result, workflow_module.WorkflowBoundaryDecision)
        self.assertEqual(result.decision, "same_workflow")
        self.assertEqual(result.decision_source, "ai")


if __name__ == "__main__":
    unittest.main()
