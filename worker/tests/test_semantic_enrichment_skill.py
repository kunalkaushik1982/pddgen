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
    / "semantic_enrichment"
    / "schemas.py"
)
SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "semantic_enrichment"
    / "skill.py"
)
CLIENT_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "client.py"
RUNTIME_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "runtime.py"
BOUNDARY_SCHEMAS_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "workflow_boundary_detection"
    / "schemas.py"
)
BOUNDARY_SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "workflow_boundary_detection"
    / "skill.py"
)
WORKFLOW_INTELLIGENCE_PATH = Path(__file__).resolve().parents[1] / "services" / "workflow_intelligence" / "__init__.py"
EVIDENCE_SEGMENTATION_PATH = Path(__file__).resolve().parents[1] / "services" / "workflow_intelligence" / "segmentation_service.py"


def load_schemas_module():
    spec = importlib.util.spec_from_file_location("semantic_enrichment_schemas", SCHEMAS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_skill_module():
    spec = importlib.util.spec_from_file_location("semantic_enrichment_skill", SKILL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_client_module():
    spec = importlib.util.spec_from_file_location("ai_skill_client_semantic", CLIENT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_runtime_module():
    spec = importlib.util.spec_from_file_location("ai_skill_runtime_semantic", RUNTIME_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_boundary_schemas_module():
    spec = importlib.util.spec_from_file_location("workflow_boundary_detection_schemas_semantic", BOUNDARY_SCHEMAS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_boundary_skill_module():
    spec = importlib.util.spec_from_file_location("workflow_boundary_detection_skill_semantic", BOUNDARY_SKILL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_workflow_intelligence_module():
    spec = importlib.util.spec_from_file_location("workflow_intelligence_local", WORKFLOW_INTELLIGENCE_PATH)
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
        def enrich_workflow_segment(self, **kwargs):
            return None

    ai_transcript_module.AITranscriptInterpreter = FakeInterpreter

    draft_support_module = types.ModuleType("worker.services.draft_generation.support")
    draft_support_module.ACTION_VERB_PATTERNS = {"review": ("review",), "create": ("create",)}
    draft_support_module.TIMESTAMP_PATTERN = None
    draft_support_module.classify_action_type = lambda text: "review"

    strategy_interfaces_module = types.ModuleType("worker.services.workflow_intelligence.strategy_interfaces")
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
    sys.modules["worker.services.ai_skills.semantic_enrichment.schemas"] = load_schemas_module()
    sys.modules["worker.services.ai_skills.semantic_enrichment.skill"] = load_skill_module()
    sys.modules["worker.services.ai_skills.workflow_boundary_detection.schemas"] = load_boundary_schemas_module()
    sys.modules["worker.services.ai_skills.workflow_boundary_detection.skill"] = load_boundary_skill_module()
    sys.modules["worker.services.draft_generation.support"] = draft_support_module
    sys.modules["worker.services.workflow_intelligence.strategy_interfaces"] = strategy_interfaces_module
    sys.modules["worker.services.workflow_intelligence"] = workflow_intelligence_module

    spec = importlib.util.spec_from_file_location("evidence_segmentation_local", EVIDENCE_SEGMENTATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, workflow_intelligence_module


class SemanticEnrichmentSchemaTests(unittest.TestCase):
    def test_semantic_enrichment_request_keeps_segment_context(self) -> None:
        schemas = load_schemas_module()
        request = schemas.SemanticEnrichmentRequest(
            transcript_name="artifact-1",
            segment_text="Open SAP and review the vendor record",
            segment_context={"segment_order": 1, "start_timestamp": "00:00:05"},
        )

        self.assertEqual(request.transcript_name, "artifact-1")
        self.assertEqual(request.segment_context["segment_order"], 1)

    def test_semantic_enrichment_response_keeps_labels(self) -> None:
        schemas = load_schemas_module()
        response = schemas.SemanticEnrichmentResponse(
            actor="User",
            actor_role="operator",
            system_name="SAP",
            action_verb="review",
            action_type="review",
            business_object="Vendor",
            workflow_goal="Review Vendor",
            rule_hints=["Validate before submit"],
            domain_terms=["vendor", "review"],
            confidence="high",
            rationale="Direct UI and object evidence",
        )

        self.assertEqual(response.system_name, "SAP")
        self.assertEqual(response.confidence, "high")

    def test_normalize_confidence_limits_values(self) -> None:
        skill = load_skill_module()

        self.assertEqual(skill.normalize_confidence("HIGH"), "high")
        self.assertEqual(skill.normalize_confidence("bad"), "medium")

    def test_build_messages_includes_segment_text(self) -> None:
        schemas = load_schemas_module()
        skill_module = load_skill_module()
        request = schemas.SemanticEnrichmentRequest(
            transcript_name="artifact-1",
            segment_text="Open SAP and review vendor",
            segment_context={"segment_order": 1},
        )

        skill = skill_module.SemanticEnrichmentSkill(client=object())
        messages = skill.build_messages(request)

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("workflow evidence segment", messages[0]["content"])
        self.assertIn("Open SAP and review vendor", messages[1]["content"])

    def test_ai_semantic_strategy_uses_skill_and_preserves_dataclass_shape(self) -> None:
        evidence_module, workflow_module = load_evidence_segmentation_module()

        class StubSemanticSkill:
            skill_id = "semantic_enrichment"
            version = "1.0"

            def run(self, input: object):
                schemas = load_schemas_module()
                return schemas.SemanticEnrichmentResponse(
                    actor="User",
                    actor_role="operator",
                    system_name="SAP",
                    action_verb="review",
                    action_type="review",
                    business_object="Vendor",
                    workflow_goal="Review Vendor",
                    rule_hints=["Validate before submit"],
                    domain_terms=["vendor", "review"],
                    confidence="high",
                    rationale="direct evidence",
                )

        strategy = evidence_module.AISemanticEnrichmentStrategy()
        strategy._semantic_enrichment_skill = StubSemanticSkill()
        segment = workflow_module.EvidenceSegment(
            id="seg-1",
            transcript_artifact_id="artifact-1",
            meeting_id=None,
            segment_order=1,
            text="Open SAP and review the vendor record",
        )

        result = strategy.enrich(segment)

        self.assertEqual(result.system_name, "SAP")
        self.assertEqual(result.enrichment_source, "ai")
        self.assertEqual(type(result).__name__, "SemanticEnrichment")


if __name__ == "__main__":
    unittest.main()
