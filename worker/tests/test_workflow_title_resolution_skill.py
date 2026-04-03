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
    / "workflow_title_resolution"
    / "schemas.py"
)
SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "workflow_title_resolution"
    / "skill.py"
)
CLIENT_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "client.py"
RUNTIME_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "runtime.py"
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "registry.py"
PROCESS_GROUPING_PATH = Path(__file__).resolve().parents[1] / "services" / "process_grouping_service.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_schemas_module():
    return load_module("workflow_title_resolution_schemas_test", SCHEMAS_PATH)


def load_skill_module():
    return load_module("workflow_title_resolution_skill_test", SKILL_PATH)


def load_client_module():
    return load_module("ai_skill_client_title_test", CLIENT_PATH)


def load_runtime_module():
    return load_module("ai_skill_runtime_title_test", RUNTIME_PATH)


def load_registry_module():
    return load_module("ai_skill_registry_title_test", REGISTRY_PATH)


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

    ai_transcript_module = types.ModuleType("worker.services.ai_transcript_interpreter")
    worker_module = types.ModuleType("worker")
    worker_module.__path__ = []  # type: ignore[attr-defined]
    worker_services_module = types.ModuleType("worker.services")
    worker_services_module.__path__ = []  # type: ignore[attr-defined]
    ai_skills_module = types.ModuleType("worker.services.ai_skills")
    ai_skills_module.__path__ = []  # type: ignore[attr-defined]
    title_pkg_module = types.ModuleType("worker.services.ai_skills.workflow_title_resolution")
    title_pkg_module.__path__ = []  # type: ignore[attr-defined]
    group_pkg_module = types.ModuleType("worker.services.ai_skills.workflow_group_match")
    group_pkg_module.__path__ = []  # type: ignore[attr-defined]

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
        pass

    ai_transcript_module.AITranscriptInterpreter = AITranscriptInterpreter
    ai_transcript_module.WorkflowTitleInterpretation = WorkflowTitleInterpretation
    ai_transcript_module.WorkflowGroupMatchInterpretation = WorkflowGroupMatchInterpretation
    ai_transcript_module.WorkflowCapabilityInterpretation = WorkflowCapabilityInterpretation

    workflow_intelligence_module = types.ModuleType("worker.services.workflow_intelligence")
    workflow_intelligence_module.EvidenceSegment = type("EvidenceSegment", (), {})
    workflow_intelligence_module.WorkflowBoundaryDecision = type("WorkflowBoundaryDecision", (), {})

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
    sys.modules["worker.services.ai_skills.workflow_title_resolution"] = title_pkg_module
    sys.modules["worker.services.ai_skills.workflow_group_match"] = group_pkg_module
    sys.modules["worker.services.ai_transcript_interpreter"] = ai_transcript_module
    sys.modules["worker.services.workflow_intelligence"] = workflow_intelligence_module
    sys.modules["worker.services.ai_skills.client"] = load_client_module()
    sys.modules["worker.services.ai_skills.runtime"] = load_runtime_module()
    sys.modules["worker.services.ai_skills.workflow_title_resolution.schemas"] = load_schemas_module()
    sys.modules["worker.services.ai_skills.workflow_title_resolution.skill"] = load_skill_module()
    group_schema_module = types.ModuleType("worker.services.ai_skills.workflow_group_match.schemas")

    @dataclass(slots=True)
    class WorkflowGroupMatchRequest:
        transcript_name: str
        workflow_summary: dict[str, object]
        existing_groups: list[dict[str, object]]

    group_schema_module.WorkflowGroupMatchRequest = WorkflowGroupMatchRequest
    sys.modules["worker.services.ai_skills.workflow_group_match.schemas"] = group_schema_module
    sys.modules["worker.services.ai_skills.registry"] = load_registry_module()

    return load_module("process_grouping_title_test", PROCESS_GROUPING_PATH)


class WorkflowTitleResolutionTests(unittest.TestCase):
    def test_workflow_title_resolution_request_keeps_summary(self) -> None:
        schemas = load_schemas_module()
        request = schemas.WorkflowTitleResolutionRequest(
            transcript_name="artifact-1",
            workflow_summary={"top_goals": ["Create Vendor"], "top_systems": ["SAP"]},
        )

        self.assertEqual(request.transcript_name, "artifact-1")
        self.assertEqual(request.workflow_summary["top_goals"], ["Create Vendor"])

    def test_workflow_title_resolution_response_keeps_title_and_slug(self) -> None:
        schemas = load_schemas_module()
        response = schemas.WorkflowTitleResolutionResponse(
            workflow_title="Vendor Creation",
            canonical_slug="vendor-creation",
            confidence="high",
            rationale="Repeated vendor creation evidence",
        )

        self.assertEqual(response.workflow_title, "Vendor Creation")
        self.assertEqual(response.canonical_slug, "vendor-creation")

    def test_normalize_confidence_limits_values(self) -> None:
        skill = load_skill_module()
        self.assertEqual(skill.normalize_confidence("HIGH"), "high")
        self.assertEqual(skill.normalize_confidence("unexpected"), "medium")

    def test_build_messages_includes_workflow_summary(self) -> None:
        schemas = load_schemas_module()
        skill_module = load_skill_module()
        request = schemas.WorkflowTitleResolutionRequest(
            transcript_name="artifact-1",
            workflow_summary={"top_goals": ["Create Vendor"]},
        )

        messages = skill_module.WorkflowTitleResolutionSkill(client=object()).build_messages(request)

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("business workflow title", messages[0]["content"])
        self.assertIn("Create Vendor", messages[1]["content"])

    def test_process_grouping_title_resolution_uses_skill_and_preserves_dataclass(self) -> None:
        grouping_module = load_process_grouping_module()
        ai_module = sys.modules["worker.services.ai_transcript_interpreter"]

        class StubWorkflowTitleSkill:
            skill_id = "workflow_title_resolution"
            version = "1.0"

            def run(self, input: object):
                schemas = load_schemas_module()
                return schemas.WorkflowTitleResolutionResponse(
                    workflow_title="Vendor Creation",
                    canonical_slug="vendor-creation",
                    confidence="high",
                    rationale="Repeated vendor evidence",
                )

        service = grouping_module.ProcessGroupingService()
        service._workflow_title_resolution_skill = StubWorkflowTitleSkill()
        transcript = grouping_module.ArtifactModel(id="artifact-1", name="artifact-1")
        profile = grouping_module.TranscriptWorkflowProfile(
            transcript_artifact_id="artifact-1",
            top_actors=[],
            top_objects=["Vendor"],
            top_systems=["SAP"],
            top_actions=["create"],
            top_goals=["Create Vendor"],
            top_rules=[],
        )

        result = service._resolve_title_with_ai(
            transcript=transcript,
            steps=[{"action_text": "Create vendor"}],
            workflow_profile=profile,
            fallback_title="Fallback Title",
        )

        self.assertEqual(result.workflow_title, "Vendor Creation")
        self.assertEqual(result.canonical_slug, "vendor-creation")
        self.assertEqual(type(result).__name__, "WorkflowTitleInterpretation")

    def test_default_registry_creates_workflow_title_resolution_skill(self) -> None:
        registry_module = load_registry_module()
        registry = registry_module.build_default_ai_skill_registry()
        self.assertEqual(registry.create("workflow_title_resolution").skill_id, "workflow_title_resolution")


if __name__ == "__main__":
    unittest.main()
