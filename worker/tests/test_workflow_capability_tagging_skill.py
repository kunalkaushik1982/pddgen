from __future__ import annotations

from dataclasses import dataclass, field
import importlib.util
from pathlib import Path
import sys
import types
import unittest

SCHEMAS_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "workflow_capability_tagging"
    / "schemas.py"
)
SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "workflow_capability_tagging"
    / "skill.py"
)
CLIENT_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "client.py"
RUNTIME_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "runtime.py"
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "registry.py"
PROCESS_GROUPING_PATH = Path(__file__).resolve().parents[1] / "services" / "workflow_intelligence" / "grouping_service.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_schemas_module():
    return load_module("workflow_capability_tagging_schemas_test", SCHEMAS_PATH)


def load_skill_module():
    return load_module("workflow_capability_tagging_skill_test", SKILL_PATH)


def load_client_module():
    return load_module("ai_skill_client_capability_tagging_test", CLIENT_PATH)


def load_runtime_module():
    return load_module("ai_skill_runtime_capability_tagging_test", RUNTIME_PATH)


def load_registry_module():
    return load_module("ai_skill_registry_capability_tagging_test", REGISTRY_PATH)


def load_process_grouping_module():
    app_module = types.ModuleType("app")
    app_module.__path__ = []  # type: ignore[attr-defined]
    core_module = types.ModuleType("app.core")
    observability_module = types.ModuleType("app.core.observability")

    class FakeLogger:
        def info(self, *args, **kwargs):
            return None

    observability_module.get_logger = lambda name: FakeLogger()

    artifact_module = types.ModuleType("app.models.artifact")
    draft_session_module = types.ModuleType("app.models.draft_session")
    process_group_model_module = types.ModuleType("app.models.process_group")

    @dataclass(slots=True)
    class ArtifactModel:
        id: str = "artifact-1"
        name: str = "artifact-1"

    @dataclass(slots=True)
    class DraftSessionModel:
        document_type: str = "pdd"

    @dataclass(slots=True)
    class ProcessGroupModel:
        id: str = "group-1"
        title: str = "Vendor Creation"
        canonical_slug: str = "vendor-creation"
        summary_text: str = ""
        capability_tags_json: str = "[]"

    artifact_module.ArtifactModel = ArtifactModel
    draft_session_module.DraftSessionModel = DraftSessionModel
    process_group_model_module.ProcessGroupModel = ProcessGroupModel

    process_group_service_module = types.ModuleType("app.services.process_group_service")

    class ProcessGroupService:
        pass

    process_group_service_module.ProcessGroupService = ProcessGroupService

    worker_module = types.ModuleType("worker")
    worker_module.__path__ = []  # type: ignore[attr-defined]
    worker_services_module = types.ModuleType("worker.services")
    worker_services_module.__path__ = []  # type: ignore[attr-defined]
    ai_skills_module = types.ModuleType("worker.services.ai_skills")
    ai_skills_module.__path__ = []  # type: ignore[attr-defined]
    process_summary_pkg = types.ModuleType("worker.services.ai_skills.process_summary_generation")
    process_summary_pkg.__path__ = []  # type: ignore[attr-defined]
    title_pkg = types.ModuleType("worker.services.ai_skills.workflow_title_resolution")
    title_pkg.__path__ = []  # type: ignore[attr-defined]
    group_pkg = types.ModuleType("worker.services.ai_skills.workflow_group_match")
    group_pkg.__path__ = []  # type: ignore[attr-defined]
    capability_pkg = types.ModuleType("worker.services.ai_skills.workflow_capability_tagging")
    capability_pkg.__path__ = []  # type: ignore[attr-defined]

    ai_transcript_module = types.ModuleType("worker.services.ai_transcript.interpreter")

    @dataclass(slots=True)
    class WorkflowTitleInterpretation:
        workflow_title: str
        canonical_slug: str
        confidence: str
        rationale: str

    @dataclass(slots=True)
    class WorkflowGroupMatchInterpretation:
        matched_existing_title: str | None
        recommended_title: str
        recommended_slug: str
        confidence: str
        rationale: str

    @dataclass(slots=True)
    class WorkflowCapabilityInterpretation:
        capability_tags: list[str] = field(default_factory=list)
        confidence: str = "unknown"
        rationale: str = ""

    class AITranscriptInterpreter:
        def classify_workflow_capabilities(self, **kwargs):
            return None

    ai_transcript_module.AITranscriptInterpreter = AITranscriptInterpreter
    ai_transcript_module.WorkflowTitleInterpretation = WorkflowTitleInterpretation
    ai_transcript_module.WorkflowGroupMatchInterpretation = WorkflowGroupMatchInterpretation
    ai_transcript_module.WorkflowCapabilityInterpretation = WorkflowCapabilityInterpretation

    workflow_intelligence_module = types.ModuleType("worker.services.workflow_intelligence")
    workflow_intelligence_module.EvidenceSegment = type("EvidenceSegment", (), {})
    workflow_intelligence_module.WorkflowBoundaryDecision = type("WorkflowBoundaryDecision", (), {})

    title_schema_module = types.ModuleType("worker.services.ai_skills.workflow_title_resolution.schemas")

    @dataclass(slots=True)
    class WorkflowTitleResolutionRequest:
        transcript_name: str
        workflow_summary: dict[str, object]

    title_schema_module.WorkflowTitleResolutionRequest = WorkflowTitleResolutionRequest

    group_schema_module = types.ModuleType("worker.services.ai_skills.workflow_group_match.schemas")

    @dataclass(slots=True)
    class WorkflowGroupMatchRequest:
        transcript_name: str
        workflow_summary: dict[str, object]
        existing_groups: list[dict[str, object]]

    group_schema_module.WorkflowGroupMatchRequest = WorkflowGroupMatchRequest

    process_summary_schema_module = types.ModuleType("worker.services.ai_skills.process_summary_generation.schemas")

    @dataclass(slots=True)
    class ProcessSummaryGenerationRequest:
        process_title: str
        workflow_summary: dict[str, object]
        steps: list[dict[str, object]]
        notes: list[dict[str, object]]
        document_type: str

    process_summary_schema_module.ProcessSummaryGenerationRequest = ProcessSummaryGenerationRequest

    sys.modules["app"] = app_module
    sys.modules["app.core"] = core_module
    sys.modules["app.core.observability"] = observability_module
    sys.modules["app.models.artifact"] = artifact_module
    sys.modules["app.models.draft_session"] = draft_session_module
    sys.modules["app.models.process_group"] = process_group_model_module
    sys.modules["app.services.process_group_service"] = process_group_service_module
    sys.modules["worker"] = worker_module
    sys.modules["worker.services"] = worker_services_module
    sys.modules["worker.services.ai_skills"] = ai_skills_module
    sys.modules["worker.services.ai_skills.process_summary_generation"] = process_summary_pkg
    sys.modules["worker.services.ai_skills.workflow_title_resolution"] = title_pkg
    sys.modules["worker.services.ai_skills.workflow_group_match"] = group_pkg
    sys.modules["worker.services.ai_skills.workflow_capability_tagging"] = capability_pkg
    sys.modules["worker.services.ai_skills.client"] = load_client_module()
    sys.modules["worker.services.ai_skills.runtime"] = load_runtime_module()
    sys.modules["worker.services.ai_skills.workflow_capability_tagging.schemas"] = load_schemas_module()
    sys.modules["worker.services.ai_skills.workflow_capability_tagging.skill"] = load_skill_module()
    sys.modules["worker.services.ai_skills.workflow_title_resolution.schemas"] = title_schema_module
    sys.modules["worker.services.ai_skills.workflow_group_match.schemas"] = group_schema_module
    sys.modules["worker.services.ai_skills.process_summary_generation.schemas"] = process_summary_schema_module
    sys.modules["worker.services.ai_transcript.interpreter"] = ai_transcript_module
    sys.modules["worker.services.workflow_intelligence"] = workflow_intelligence_module
    sys.modules["worker.services.ai_skills.registry"] = load_registry_module()

    return load_module("process_grouping_capability_tagging_test", PROCESS_GROUPING_PATH)


class WorkflowCapabilityTaggingTests(unittest.TestCase):
    def test_capability_tagging_request_keeps_workflow_inputs(self) -> None:
        schemas = load_schemas_module()
        request = schemas.WorkflowCapabilityTaggingRequest(
            process_title="Vendor Creation",
            workflow_summary={"top_goals": ["Create vendor"]},
            document_type="pdd",
        )
        self.assertEqual(request.process_title, "Vendor Creation")
        self.assertEqual(request.document_type, "pdd")

    def test_capability_tagging_response_keeps_result_fields(self) -> None:
        schemas = load_schemas_module()
        response = schemas.WorkflowCapabilityTaggingResponse(
            capability_tags=["Procurement", "Vendor Management"],
            confidence="high",
            rationale="Workflow aligns to procurement capabilities.",
        )
        self.assertEqual(response.capability_tags, ["Procurement", "Vendor Management"])
        self.assertEqual(response.confidence, "high")

    def test_normalize_confidence_limits_values(self) -> None:
        skill = load_skill_module()
        self.assertEqual(skill.normalize_confidence("HIGH"), "high")
        self.assertEqual(skill.normalize_confidence("bad"), "medium")

    def test_normalize_capability_tags_excludes_process_title(self) -> None:
        skill = load_skill_module()
        tags = skill.normalize_capability_tags(
            ["Vendor Creation", "Procurement", "procurement", "Vendor Management"],
            process_title="Vendor Creation",
        )
        self.assertEqual(tags, ["Procurement", "Vendor Management"])

    def test_build_messages_includes_capability_context(self) -> None:
        schemas = load_schemas_module()
        skill_module = load_skill_module()
        request = schemas.WorkflowCapabilityTaggingRequest(
            process_title="Vendor Creation",
            workflow_summary={"top_goals": ["Create vendor"]},
            document_type="pdd",
        )
        messages = skill_module.WorkflowCapabilityTaggingSkill(client=object()).build_messages(request)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("business capability tags", messages[0]["content"])
        self.assertIn("Vendor Creation", messages[1]["content"])

    def test_grouping_service_uses_capability_skill_when_confident(self) -> None:
        grouping_module = load_process_grouping_module()

        class StubCapabilitySkill:
            skill_id = "workflow_capability_tagging"
            version = "1.0"

            def run(self, input: object):
                schemas = load_schemas_module()
                return schemas.WorkflowCapabilityTaggingResponse(
                    capability_tags=["Procurement", "Vendor Management"],
                    confidence="high",
                    rationale="clear evidence",
                )

        service = grouping_module.ProcessGroupingService()
        service._workflow_capability_tagging_skill = StubCapabilitySkill()
        result = service._resolve_capability_tags(
            process_title="Vendor Creation",
            workflow_summary={"top_goals": ["Create vendor"]},
            workflow_profiles=[],
            document_type="pdd",
        )
        self.assertEqual(result, ["Procurement", "Vendor Management"])

    def test_grouping_service_falls_back_when_capability_skill_is_weak(self) -> None:
        grouping_module = load_process_grouping_module()

        class StubCapabilitySkill:
            skill_id = "workflow_capability_tagging"
            version = "1.0"

            def run(self, input: object):
                schemas = load_schemas_module()
                return schemas.WorkflowCapabilityTaggingResponse(
                    capability_tags=["Procurement"],
                    confidence="low",
                    rationale="weak evidence",
                )

        service = grouping_module.ProcessGroupingService()
        service._workflow_capability_tagging_skill = StubCapabilitySkill()
        profile = grouping_module.TranscriptWorkflowProfile(
            transcript_artifact_id="artifact-1",
            top_actors=[],
            top_objects=[],
            top_systems=[],
            top_actions=[],
            top_goals=[],
            top_rules=[],
            top_domain_terms=["supplier onboarding"],
        )
        result = service._resolve_capability_tags(
            process_title="Vendor Creation",
            workflow_summary={"top_goals": ["Create vendor"]},
            workflow_profiles=[profile],
            document_type="pdd",
        )
        self.assertEqual(result, ["Supplier Onboarding"])

    def test_grouping_service_falls_back_to_process_title_when_no_tags_exist(self) -> None:
        grouping_module = load_process_grouping_module()

        class StubCapabilitySkill:
            skill_id = "workflow_capability_tagging"
            version = "1.0"

            def run(self, input: object):
                schemas = load_schemas_module()
                return schemas.WorkflowCapabilityTaggingResponse(
                    capability_tags=[],
                    confidence="high",
                    rationale="no reusable capability found",
                )

        service = grouping_module.ProcessGroupingService()
        service._workflow_capability_tagging_skill = StubCapabilitySkill()
        result = service._resolve_capability_tags(
            process_title="Vendor Creation",
            workflow_summary={"top_goals": ["Create vendor"]},
            workflow_profiles=[],
            document_type="pdd",
        )
        self.assertEqual(result, ["Vendor Creation"])

    def test_default_registry_creates_workflow_capability_tagging_skill(self) -> None:
        registry_module = load_registry_module()
        registry = registry_module.build_default_ai_skill_registry()
        self.assertEqual(registry.create("workflow_capability_tagging").skill_id, "workflow_capability_tagging")


if __name__ == "__main__":
    unittest.main()
