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
    / "transcript_to_steps"
    / "schemas.py"
)
SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "transcript_to_steps"
    / "skill.py"
)
CLIENT_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "client.py"
RUNTIME_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "runtime.py"
INTERPRETER_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript_interpreter.py"
GENERATION_TYPES_PATH = Path(__file__).resolve().parents[1] / "services" / "generation_types.py"
AI_TRANSCRIPT_INIT_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript" / "__init__.py"
AI_TRANSCRIPT_CLIENT_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript" / "client.py"
AI_TRANSCRIPT_MODELS_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript" / "models.py"
AI_TRANSCRIPT_NORMALIZATION_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript" / "normalization.py"
AI_TRANSCRIPT_DIAGRAMS_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript" / "diagrams.py"
AI_TRANSCRIPT_WORKFLOWS_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript" / "workflows.py"


def load_schemas_module():
    spec = importlib.util.spec_from_file_location("transcript_to_steps_schemas", SCHEMAS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_skill_module():
    spec = importlib.util.spec_from_file_location("transcript_to_steps_skill", SKILL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_client_module():
    spec = importlib.util.spec_from_file_location("ai_skill_client", CLIENT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_runtime_module():
    spec = importlib.util.spec_from_file_location("ai_skill_runtime", RUNTIME_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_generation_types_module():
    spec = importlib.util.spec_from_file_location("worker.services.generation_types", GENERATION_TYPES_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_service_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_interpreter_module():
    worker_module = types.ModuleType("worker")
    worker_module.__path__ = []  # type: ignore[attr-defined]
    services_module = types.ModuleType("worker.services")
    services_module.__path__ = []  # type: ignore[attr-defined]
    ai_skills_module = types.ModuleType("worker.services.ai_skills")
    ai_skills_module.__path__ = []  # type: ignore[attr-defined]
    ai_transcript_module = types.ModuleType("worker.services.ai_transcript")
    ai_transcript_module.__path__ = []  # type: ignore[attr-defined]
    transcript_module = types.ModuleType("worker.services.ai_skills.transcript_to_steps")
    transcript_module.__path__ = []  # type: ignore[attr-defined]
    bootstrap_module = types.ModuleType("worker.bootstrap")

    class FakeSettings:
        ai_enabled = True
        ai_api_key = "test-key"
        ai_base_url = "https://example.invalid"
        ai_model = "test-model"
        ai_timeout_seconds = 30

    bootstrap_module.get_backend_settings = lambda: FakeSettings()
    worker_module.bootstrap = bootstrap_module

    httpx_module = types.ModuleType("httpx")

    class Timeout:
        def __init__(self, value: object) -> None:
            self.value = value

    class Client:
        def __init__(self, timeout: object | None = None) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    httpx_module.Timeout = Timeout
    httpx_module.Client = Client
    httpx_module.TimeoutException = Exception
    httpx_module.HTTPStatusError = Exception
    httpx_module.HTTPError = Exception

    sys.modules["worker"] = worker_module
    sys.modules["worker.services"] = services_module
    sys.modules["worker.services.ai_skills"] = ai_skills_module
    sys.modules["worker.services.ai_transcript"] = ai_transcript_module
    sys.modules["worker.services.ai_skills.transcript_to_steps"] = transcript_module
    sys.modules["worker.bootstrap"] = bootstrap_module
    sys.modules["httpx"] = httpx_module
    sys.modules["worker.services.generation_types"] = load_generation_types_module()
    _load_service_module("worker.services.ai_transcript.client", AI_TRANSCRIPT_CLIENT_PATH)
    _load_service_module("worker.services.ai_transcript.models", AI_TRANSCRIPT_MODELS_PATH)
    _load_service_module("worker.services.ai_transcript.normalization", AI_TRANSCRIPT_NORMALIZATION_PATH)
    _load_service_module("worker.services.ai_transcript.diagrams", AI_TRANSCRIPT_DIAGRAMS_PATH)
    _load_service_module("worker.services.ai_transcript.workflows", AI_TRANSCRIPT_WORKFLOWS_PATH)
    _load_service_module("worker.services.ai_transcript", AI_TRANSCRIPT_INIT_PATH)
    sys.modules["worker.services.ai_skills.client"] = load_client_module()
    sys.modules["worker.services.ai_skills.runtime"] = load_runtime_module()
    sys.modules["worker.services.ai_skills.transcript_to_steps.schemas"] = load_schemas_module()
    sys.modules["worker.services.ai_skills.transcript_to_steps.skill"] = load_skill_module()

    spec = importlib.util.spec_from_file_location("ai_transcript_interpreter", INTERPRETER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TranscriptToStepsSchemaTests(unittest.TestCase):
    def test_transcript_to_steps_response_holds_steps_and_notes(self) -> None:
        schemas = load_schemas_module()
        response = schemas.TranscriptToStepsResponse(
            steps=[
                schemas.TranscriptStep(
                    application_name="SAP",
                    action_text="Open vendor transaction",
                    source_data_note="",
                    start_timestamp="00:00:05",
                    end_timestamp="00:00:08",
                    display_timestamp="00:00:05",
                    supporting_transcript_text="Open vendor transaction",
                    confidence="high",
                )
            ],
            notes=[
                schemas.TranscriptNote(
                    text="Vendor must exist first",
                    confidence="medium",
                    inference_type="inferred",
                )
            ],
        )

        self.assertEqual(response.steps[0].application_name, "SAP")
        self.assertEqual(response.notes[0].inference_type, "inferred")

    def test_transcript_to_steps_request_keeps_transcript_input(self) -> None:
        schemas = load_schemas_module()
        request = schemas.TranscriptToStepsRequest(
            transcript_artifact_id="artifact-1",
            transcript_text="00:00:01 Open SAP",
        )

        self.assertEqual(request.transcript_artifact_id, "artifact-1")
        self.assertIn("Open SAP", request.transcript_text)

    def test_normalize_confidence_limits_values(self) -> None:
        skill = load_skill_module()

        self.assertEqual(skill.normalize_confidence("HIGH"), "high")
        self.assertEqual(skill.normalize_confidence("bad-value"), "medium")

    def test_normalize_timestamp_converts_hms(self) -> None:
        skill = load_skill_module()

        self.assertEqual(skill.normalize_timestamp("1:02:03"), "01:02:03")
        self.assertEqual(skill.normalize_timestamp(""), "")

    def test_build_messages_includes_prompt_and_transcript(self) -> None:
        schemas = load_schemas_module()
        skill_module = load_skill_module()
        request = schemas.TranscriptToStepsRequest(
            transcript_artifact_id="artifact-1",
            transcript_text="00:00:01 Open SAP",
        )

        skill = skill_module.TranscriptToStepsSkill(client=object())
        messages = skill.build_messages(request)

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("structured process steps", messages[0]["content"])
        self.assertIn("Open SAP", messages[1]["content"])

    def test_interpret_uses_transcript_skill_and_preserves_legacy_shape(self) -> None:
        interpreter_module = load_interpreter_module()
        schemas = load_schemas_module()

        class StubTranscriptSkill:
            skill_id = "transcript_to_steps"
            version = "1.0"

            def run(self, input: object) -> object:
                return schemas.TranscriptToStepsResponse(
                    steps=[
                        schemas.TranscriptStep(
                            application_name="SAP",
                            action_text="Open vendor transaction",
                            source_data_note="",
                            start_timestamp="00:00:05",
                            end_timestamp="00:00:06",
                            display_timestamp="00:00:05",
                            supporting_transcript_text="Open vendor transaction",
                            confidence="high",
                        )
                    ],
                    notes=[
                        schemas.TranscriptNote(
                            text="Vendor must exist",
                            confidence="medium",
                            inference_type="inferred",
                        )
                    ],
                )

        interpreter = interpreter_module.AITranscriptInterpreter()
        interpreter._transcript_to_steps_skill = StubTranscriptSkill()
        interpreter.is_enabled = lambda: True

        result = interpreter.interpret(
            transcript_artifact_id="artifact-1",
            transcript_text="00:00:05 Open vendor transaction",
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.steps[0]["application_name"], "SAP")
        self.assertEqual(result.steps[0]["timestamp"], "00:00:05")
        self.assertEqual(result.notes[0]["text"], "Vendor must exist")


if __name__ == "__main__":
    unittest.main()
