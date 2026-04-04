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
    / "workflow_group_match"
    / "schemas.py"
)
SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "workflow_group_match"
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
    return load_module("workflow_group_match_schemas_test", SCHEMAS_PATH)


def load_skill_module():
    return load_module("workflow_group_match_skill_test", SKILL_PATH)


def load_client_module():
    return load_module("ai_skill_client_group_match_test", CLIENT_PATH)


def load_runtime_module():
    return load_module("ai_skill_runtime_group_match_test", RUNTIME_PATH)


def load_registry_module():
    return load_module("ai_skill_registry_group_match_test", REGISTRY_PATH)


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
        summary_text: str = "vendor creation sap"
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
    title_pkg_module = types.ModuleType("worker.ai_skills.workflow_title_resolution")
    title_pkg_module.__path__ = []  # type: ignore[attr-defined]
    group_pkg_module = types.ModuleType("worker.ai_skills.workflow_group_match")
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
    sys.modules["worker.ai_skills.workflow_title_resolution"] = title_pkg_module
    sys.modules["worker.ai_skills.workflow_group_match"] = group_pkg_module
    sys.modules["worker.services.ai_transcript_interpreter"] = ai_transcript_module
    sys.modules["worker.services.workflow_intelligence"] = workflow_intelligence_module
    sys.modules["worker.ai_skills.client"] = load_client_module()
    sys.modules["worker.ai_skills.runtime"] = load_runtime_module()
    title_schema_module = types.ModuleType("worker.ai_skills.workflow_title_resolution.schemas")

    @dataclass(slots=True)
    class WorkflowTitleResolutionRequest:
        transcript_name: str
        workflow_summary: dict[str, object]

    title_schema_module.WorkflowTitleResolutionRequest = WorkflowTitleResolutionRequest
    sys.modules["worker.ai_skills.workflow_title_resolution.schemas"] = title_schema_module
    sys.modules["worker.ai_skills.workflow_group_match.schemas"] = load_schemas_module()
    sys.modules["worker.ai_skills.workflow_group_match.skill"] = load_skill_module()
    sys.modules["worker.ai_skills.registry"] = load_registry_module()

    return load_module("process_grouping_group_match_test", PROCESS_GROUPING_PATH)


class StubClient:
    def __init__(self, content: dict[str, object]) -> None:
        self._content = content

    def post_json(self, *, messages: list[dict[str, str]]) -> dict[str, object]:
        return {"choices": [{"message": {"content": str(self._content).replace("'", '"')}}]}


class WorkflowGroupMatchTests(unittest.TestCase):
    def test_workflow_group_match_request_keeps_existing_groups(self) -> None:
        schemas = load_schemas_module()
        request = schemas.WorkflowGroupMatchRequest(
            transcript_name="artifact-1",
            workflow_summary={"top_systems": ["SAP"]},
            existing_groups=[{"title": "Vendor Creation"}],
        )

        self.assertEqual(request.transcript_name, "artifact-1")
        self.assertEqual(request.existing_groups[0]["title"], "Vendor Creation")

    def test_workflow_group_match_response_keeps_match_fields(self) -> None:
        schemas = load_schemas_module()
        response = schemas.WorkflowGroupMatchResponse(
            matched_existing_title="Vendor Creation",
            recommended_title="Vendor Creation",
            recommended_slug="vendor-creation",
            confidence="high",
            rationale="Same system and outcome",
        )

        self.assertEqual(response.matched_existing_title, "Vendor Creation")
        self.assertEqual(response.recommended_slug, "vendor-creation")

    def test_group_match_rejects_non_exact_existing_title(self) -> None:
        schemas = load_schemas_module()
        skill_module = load_skill_module()
        request = schemas.WorkflowGroupMatchRequest(
            transcript_name="artifact-1",
            workflow_summary={"top_systems": ["SAP"]},
            existing_groups=[{"title": "Vendor Creation"}],
        )

        skill = skill_module.WorkflowGroupMatchSkill(
            client=StubClient(
                {
                    "matched_existing_title": "vendor creation",
                    "recommended_title": "Vendor Creation",
                    "recommended_slug": "vendor-creation",
                    "confidence": "high",
                    "rationale": "same workflow",
                }
            )
        )
        result = skill.run(request)
        self.assertIsNone(result.matched_existing_title)

    def test_build_messages_includes_existing_groups(self) -> None:
        schemas = load_schemas_module()
        skill_module = load_skill_module()
        request = schemas.WorkflowGroupMatchRequest(
            transcript_name="artifact-1",
            workflow_summary={"top_systems": ["SAP"]},
            existing_groups=[{"title": "Vendor Creation"}],
        )

        messages = skill_module.WorkflowGroupMatchSkill(client=object()).build_messages(request)

        self.assertIn("existing_group_titles", messages[1]["content"])
        self.assertIn("Vendor Creation", messages[1]["content"])

    def test_process_grouping_group_match_uses_skill(self) -> None:
        grouping_module = load_process_grouping_module()

        class StubWorkflowGroupMatchSkill:
            skill_id = "workflow_group_match"
            version = "1.0"

            def run(self, input: object):
                schemas = load_schemas_module()
                return schemas.WorkflowGroupMatchResponse(
                    matched_existing_title="Vendor Creation",
                    recommended_title="Vendor Creation",
                    recommended_slug="vendor-creation",
                    confidence="high",
                    rationale="Same system and outcome",
                )

        service = grouping_module.ProcessGroupingService()
        service._workflow_group_match_skill = StubWorkflowGroupMatchSkill()
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
        title_resolution = grouping_module.WorkflowTitleInterpretation(
            workflow_title="Vendor Creation",
            canonical_slug="vendor-creation",
            confidence="high",
            rationale="",
        )
        existing_group = grouping_module.ProcessGroupModel(
            id="group-1",
            title="Vendor Creation",
            canonical_slug="vendor-creation",
            summary_text="vendor creation sap",
        )
        heuristic_match = {
            "matched_group": None,
            "best_score": 0.7,
            "ambiguity": False,
            "candidate_matches": [{"group_title": "Vendor Creation", "score": 0.7}],
            "supporting_signals": ["moderate_existing_group_match"],
        }

        result = service._match_existing_group_with_ai(
            transcript=transcript,
            title_resolution=title_resolution,
            workflow_profile=profile,
            steps=[],
            notes=[],
            existing_groups=[existing_group],
            heuristic_match=heuristic_match,
        )

        self.assertIsInstance(result, grouping_module.GroupResolutionDecision)
        self.assertEqual(result.ai_decision, "matched_existing_group")

    def test_default_registry_creates_workflow_group_match_skill(self) -> None:
        registry_module = load_registry_module()
        registry = registry_module.build_default_ai_skill_registry()
        self.assertEqual(registry.create("workflow_group_match").skill_id, "workflow_group_match")


if __name__ == "__main__":
    unittest.main()
