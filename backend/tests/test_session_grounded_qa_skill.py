from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from typing import cast
from pathlib import Path
import sys
import types
import unittest

from app.core.config import Settings

SCHEMAS_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "ai_skills"
    / "session_grounded_qa"
    / "schemas.py"
)
SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "ai_skills"
    / "session_grounded_qa"
    / "skill.py"
)
SESSION_CHAT_PATH = Path(__file__).resolve().parents[1] / "app" / "services" / "chat" / "session_chat_service.py"

_BACKEND_STUB_KEYS = (
    "app",
    "app.core",
    "app.core.config",
    "app.core.observability",
    "app.core.llm_usage",
    "app.services",
    "app.services.ai_skills",
    "app.services.ai_skills.session_grounded_qa",
    "app.services.ai_skills.session_grounded_qa.schemas",
    "app.services.ai_skills.session_grounded_qa.skill",
    "app.models",
    "app.models.draft_session",
    "app.storage",
    "app.storage.storage_service",
    "httpx",
)
_backend_stub_depth = 0
_backend_stub_saved: dict[str, types.ModuleType | None] | None = None


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_schemas_module():
    return load_module("session_grounded_qa_schemas_test", SCHEMAS_PATH)


def install_backend_stubs():
    global _backend_stub_depth, _backend_stub_saved
    if _backend_stub_depth == 0:
        _backend_stub_saved = {k: sys.modules.get(k) for k in _BACKEND_STUB_KEYS}
    _backend_stub_depth += 1

    app_module = types.ModuleType("app")
    app_module.__path__ = []  # type: ignore[attr-defined]
    core_module = types.ModuleType("app.core")
    config_module = types.ModuleType("app.core.config")
    observability_module = types.ModuleType("app.core.observability")
    services_module = types.ModuleType("app.services")
    services_module.__path__ = []  # type: ignore[attr-defined]
    ai_skills_module = types.ModuleType("app.services.ai_skills")
    ai_skills_module.__path__ = []  # type: ignore[attr-defined]
    grounded_pkg = types.ModuleType("app.services.ai_skills.session_grounded_qa")
    grounded_pkg.__path__ = []  # type: ignore[attr-defined]
    models_module = types.ModuleType("app.models")
    models_module.__path__ = []  # type: ignore[attr-defined]
    draft_session_module = types.ModuleType("app.models.draft_session")
    storage_pkg = types.ModuleType("app.storage")
    storage_pkg.__path__ = []  # type: ignore[attr-defined]
    storage_service_module = types.ModuleType("app.storage.storage_service")
    httpx_module = types.ModuleType("httpx")

    class FakeSettings:
        ai_enabled = True
        ai_api_key = "test-key"
        ai_base_url = "https://example.test/v1"
        ai_model = "test-model"
        ai_timeout_seconds = 30

    config_module.Settings = FakeSettings

    class FakeLogger:
        def info(self, *args, **kwargs):
            return None

    class StorageService:
        def read_text(self, path: str) -> str:
            return ""

    class Timeout:
        def __init__(self, value: object) -> None:
            self.value = value

    class TimeoutException(Exception):
        pass

    class HTTPError(Exception):
        pass

    class HTTPStatusError(HTTPError):
        def __init__(self, response: object | None = None) -> None:
            super().__init__()
            self.response = response

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, *args, **kwargs):
            raise AssertionError("Test should inject a client when executing network calls.")

    llm_usage_module = types.ModuleType("app.core.llm_usage")

    def _noop_llm_usage(*args, **kwargs):
        return None

    llm_usage_module.log_chat_completion_usage = _noop_llm_usage  # type: ignore[attr-defined]

    config_module.get_settings = lambda: FakeSettings()
    observability_module.get_logger = lambda name: FakeLogger()
    draft_session_module.DraftSessionModel = object
    storage_service_module.StorageService = StorageService
    httpx_module.Timeout = Timeout
    httpx_module.TimeoutException = TimeoutException
    httpx_module.HTTPError = HTTPError
    httpx_module.HTTPStatusError = HTTPStatusError
    httpx_module.Client = Client

    sys.modules["app"] = app_module
    sys.modules["app.core"] = core_module
    sys.modules["app.core.config"] = config_module
    sys.modules["app.core.observability"] = observability_module
    sys.modules["app.core.llm_usage"] = llm_usage_module
    sys.modules["app.services"] = services_module
    sys.modules["app.services.ai_skills"] = ai_skills_module
    sys.modules["app.services.ai_skills.session_grounded_qa"] = grounded_pkg
    sys.modules["app.models"] = models_module
    sys.modules["app.models.draft_session"] = draft_session_module
    sys.modules["app.storage"] = storage_pkg
    sys.modules["app.storage.storage_service"] = storage_service_module
    sys.modules["httpx"] = httpx_module
    sys.modules["app.services.ai_skills.session_grounded_qa.schemas"] = load_schemas_module()

    return FakeSettings


def _restore_backend_stubs() -> None:
    global _backend_stub_depth, _backend_stub_saved
    if _backend_stub_depth == 0:
        return
    _backend_stub_depth -= 1
    if _backend_stub_depth == 0 and _backend_stub_saved is not None:
        for key, previous in _backend_stub_saved.items():
            if previous is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = previous
        _backend_stub_saved = None
        for name in (
            "session_grounded_qa_schemas_test",
            "session_grounded_qa_skill_test",
            "session_chat_service_test",
        ):
            sys.modules.pop(name, None)


def load_skill_module():
    install_backend_stubs()
    return load_module("session_grounded_qa_skill_test", SKILL_PATH)


def load_session_chat_module():
    install_backend_stubs()
    sys.modules["app.services.ai_skills.session_grounded_qa.skill"] = load_skill_module()
    return load_module("session_chat_service_test", SESSION_CHAT_PATH)


class StubClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def post(self, endpoint: str, *, headers: dict[str, str], json: dict[str, object]):
        class Response:
            def __init__(self, payload: dict[str, object]) -> None:
                self._payload = payload
                self.status_code = 200

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {"choices": [{"message": {"content": str(self._payload).replace("'", '"')}}]}

        return Response(self.payload)


class SessionGroundedQATests(unittest.TestCase):
    def tearDown(self) -> None:
        while _backend_stub_depth > 0:
            _restore_backend_stubs()

    def test_session_grounded_qa_request_keeps_inputs(self) -> None:
        schemas = load_schemas_module()
        request = schemas.SessionGroundedQARequest(
            session_id="session-1",
            session_title="Quarterly Procurement Review",
            process_group_id="group-1",
            question="What is the approval step?",
            evidence=[{"id": "step-1", "source_type": "step", "title": "Step 1", "content": "Approve PO"}],
        )
        self.assertEqual(request.session_title, "Quarterly Procurement Review")
        self.assertEqual(request.question, "What is the approval step?")

    def test_session_grounded_qa_response_keeps_outputs(self) -> None:
        schemas = load_schemas_module()
        response = schemas.SessionGroundedQAResponse(
            answer="The approval happens after purchase order review.",
            confidence="high",
            citation_ids=["step-1"],
        )
        self.assertEqual(response.confidence, "high")
        self.assertEqual(response.citation_ids, ["step-1"])

    def test_normalize_confidence_limits_values(self) -> None:
        skill = load_skill_module()
        self.assertEqual(skill.normalize_confidence("HIGH"), "high")
        self.assertEqual(skill.normalize_confidence("bad"), "medium")

    def test_normalize_citation_ids_filters_blank_values(self) -> None:
        skill = load_skill_module()
        self.assertEqual(skill.normalize_citation_ids(["step-1", "", None, "note-1"]), ["step-1", "note-1"])

    def test_build_messages_includes_question_and_evidence(self) -> None:
        schemas = load_schemas_module()
        skill_module = load_skill_module()

        class FakeSettings:
            ai_enabled = True
            ai_api_key = "test-key"
            ai_base_url = "https://example.test/v1"
            ai_model = "test-model"
            ai_timeout_seconds = 30

        request = schemas.SessionGroundedQARequest(
            session_id="session-1",
            session_title="Quarterly Procurement Review",
            process_group_id="group-1",
            question="What is the approval step?",
            evidence=[{"id": "step-1", "source_type": "step", "title": "Step 1", "content": "Approve PO"}],
        )
        messages = skill_module.SessionGroundedQASkill(
            client=None,
            settings=cast(Settings, FakeSettings()),
        ).build_messages(request)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Use only the supplied evidence", messages[0]["content"])
        self.assertIn("What is the approval step?", messages[1]["content"])

    def test_session_chat_service_uses_grounded_qa_skill(self) -> None:
        chat_module = load_session_chat_module()

        @dataclass
        class Step:
            step_number: int
            process_group_id: str | None = None
            meeting_id: str | None = None
            application_name: str = "SAP"
            action_text: str = "Approve purchase order"
            source_data_note: str = ""
            timestamp: str = ""
            supporting_transcript_text: str = "Approve the PO after review."

        @dataclass
        class Note:
            text: str
            process_group_id: str | None = None
            meeting_id: str | None = None

        @dataclass
        class Artifact:
            kind: str
            name: str
            storage_path: str
            meeting_id: str | None = None

        @dataclass
        class Session:
            id: str
            title: str
            process_steps: list[Step]
            process_notes: list[Note]
            artifacts: list[Artifact]

        class FakeStorageService:
            def read_text(self, path: str) -> str:
                return "Approve purchase order after manager review."

        class StubSessionGroundedQASkill:
            skill_id = "session_grounded_qa"
            version = "1.0"

            def run(self, input: object):
                schemas = load_schemas_module()
                return (
                    schemas.SessionGroundedQAResponse(
                        answer="The approval happens after review.",
                        confidence="high",
                        citation_ids=["step-1", "missing-id"],
                    ),
                    {},
                )

        service = chat_module.SessionChatService(storage_service=FakeStorageService(), llm_http_client=None)
        service._session_grounded_qa_skill = StubSessionGroundedQASkill()
        session = Session(
            id="session-1",
            title="Quarterly Procurement Review",
            process_steps=[Step(step_number=1)],
            process_notes=[Note(text="Manager review is required.")],
            artifacts=[Artifact(kind="transcript", name="Meeting 1", storage_path="transcript.txt")],
        )

        response = service.ask(session=session, question="What is the approval step?")
        self.assertEqual(response["answer"], "The approval happens after review.")
        self.assertEqual(response["confidence"], "high")
        self.assertEqual(response["citations"][0]["id"], "step-1")
        self.assertEqual(len(response["citations"]), 1)

    def test_session_chat_service_falls_back_for_blank_answer(self) -> None:
        chat_module = load_session_chat_module()

        @dataclass
        class Step:
            step_number: int
            process_group_id: str | None = None
            meeting_id: str | None = None
            application_name: str = "SAP"
            action_text: str = "Approve purchase order"
            source_data_note: str = ""
            timestamp: str = ""
            supporting_transcript_text: str = "Approve the PO after review."

        @dataclass
        class Session:
            id: str
            title: str
            process_steps: list[Step]
            process_notes: list[object]
            artifacts: list[object]

        class FakeStorageService:
            def read_text(self, path: str) -> str:
                return ""

        class StubSessionGroundedQASkill:
            skill_id = "session_grounded_qa"
            version = "1.0"

            def run(self, input: object):
                schemas = load_schemas_module()
                return (schemas.SessionGroundedQAResponse(answer="", confidence="low", citation_ids=[]), {})

        service = chat_module.SessionChatService(storage_service=FakeStorageService(), llm_http_client=None)
        service._session_grounded_qa_skill = StubSessionGroundedQASkill()
        session = Session(
            id="session-1",
            title="Quarterly Procurement Review",
            process_steps=[Step(step_number=1)],
            process_notes=[],
            artifacts=[],
        )

        response = service.ask(session=session, question="What is the approval step?")
        self.assertEqual(response["answer"], "The session evidence did not support a confident answer.")


if __name__ == "__main__":
    unittest.main()
