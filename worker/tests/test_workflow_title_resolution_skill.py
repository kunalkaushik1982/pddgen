from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

_AI_SKILLS_ROOT = Path(__file__).resolve().parents[1] / "ai_skills"
SCHEMAS_PATH = _AI_SKILLS_ROOT / "workflow_title_resolution" / "schemas.py"
SKILL_PATH = _AI_SKILLS_ROOT / "workflow_title_resolution" / "skill.py"
CLIENT_PATH = _AI_SKILLS_ROOT / "client.py"
RUNTIME_PATH = _AI_SKILLS_ROOT / "runtime.py"
REGISTRY_PATH = _AI_SKILLS_ROOT / "registry.py"


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
        from types import SimpleNamespace
        from unittest.mock import Mock

        from worker.tests.import_cleanup import clear_stub_modules_for_integration_tests

        clear_stub_modules_for_integration_tests()

        from app.services.process_group_service import ProcessGroupService
        from worker.ai_skills.registry import build_default_ai_skill_registry
        from worker.ai_skills.transcript_interpreter.interpreter import AITranscriptInterpreter
        from worker.grouping.grouping_identity_flow import resolve_title_with_ai
        from worker.grouping.grouping_models import TranscriptWorkflowProfile
        from worker.grouping.grouping_service import ProcessGroupingService

        class StubWorkflowTitleSkill:
            skill_id = "workflow_title_resolution"
            version = "1.0"

            def run(self, input: object):
                from worker.ai_skills.transcript_interpreter.interpreter import WorkflowTitleInterpretation

                return WorkflowTitleInterpretation(
                    workflow_title="Vendor Creation",
                    canonical_slug="vendor-creation",
                    confidence="high",
                    rationale="Repeated vendor evidence",
                )

        service = ProcessGroupingService(
            process_group_service=ProcessGroupService(),
            ai_transcript_interpreter=Mock(spec=AITranscriptInterpreter),
            ai_skill_registry=build_default_ai_skill_registry(),
        )
        service._workflow_title_resolution_skill = StubWorkflowTitleSkill()
        transcript = SimpleNamespace(id="artifact-1", name="artifact-1")
        profile = TranscriptWorkflowProfile(
            transcript_artifact_id="artifact-1",
            top_actors=[],
            top_objects=["Vendor"],
            top_systems=["SAP"],
            top_actions=["create"],
            top_goals=["Create Vendor"],
            top_rules=[],
        )

        result = resolve_title_with_ai(
            service,
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
