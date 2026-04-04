from __future__ import annotations

from dataclasses import dataclass, field
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest

BUILDER_PATH = Path(__file__).resolve().parents[1] / "services" / "screenshot_generation" / "context_builder.py"
WORKER_ROOT = Path(__file__).resolve().parents[1]
SERVICES_ROOT = WORKER_ROOT / "services"


def load_builder_module():
    app_module = types.ModuleType("app")
    app_module.__path__ = []  # type: ignore[attr-defined]
    app_models_module = types.ModuleType("app.models")
    app_models_module.__path__ = []  # type: ignore[attr-defined]
    worker_module = types.ModuleType("worker")
    worker_module.__path__ = [str(WORKER_ROOT)]  # type: ignore[attr-defined]
    services_module = types.ModuleType("worker.services")
    services_module.__path__ = [str(SERVICES_ROOT)]  # type: ignore[attr-defined]
    bootstrap_module = types.ModuleType("worker.bootstrap")
    context_module = types.ModuleType("worker.pipeline.stages.stage_context")
    generation_types_module = types.ModuleType("worker.pipeline.types")
    sqlalchemy_module = types.ModuleType("sqlalchemy")

    class _DeleteStatement:
        def where(self, *args, **kwargs):
            return self

    sqlalchemy_module.delete = lambda *args, **kwargs: _DeleteStatement()

    artifact_module = types.ModuleType("app.models.artifact")
    artifact_module.ArtifactModel = type("ArtifactModel", (), {"session_id": "session_id", "kind": "kind"})
    process_step_module = types.ModuleType("app.models.process_step")
    process_step_module.ProcessStepModel = type("ProcessStepModel", (), {})
    screenshot_module = types.ModuleType("app.models.process_step_screenshot")
    screenshot_module.ProcessStepScreenshotModel = type("ProcessStepScreenshotModel", (), {"step_id": type("StepId", (), {"in_": staticmethod(lambda ids: ids)})()})
    screenshot_candidate_module = types.ModuleType("app.models.process_step_screenshot_candidate")
    screenshot_candidate_module.ProcessStepScreenshotCandidateModel = type(
        "ProcessStepScreenshotCandidateModel",
        (),
        {"step_id": type("StepId", (), {"in_": staticmethod(lambda ids: ids)})()},
    )

    @dataclass(slots=True)
    class DraftGenerationContext:
        session_id: str
        session: object
        transcript_artifacts: list[object] = field(default_factory=list)
        video_artifacts: list[object] = field(default_factory=list)
        all_steps: list[dict] = field(default_factory=list)
        all_notes: list[dict] = field(default_factory=list)
        steps_by_transcript: dict[str, list[dict]] = field(default_factory=dict)
        persisted_step_models: list[object] = field(default_factory=list)

    context_module.DraftGenerationContext = DraftGenerationContext
    generation_types_module.StepRecord = dict

    worker_module.bootstrap = bootstrap_module
    sys.modules["app"] = app_module
    sys.modules["app.models"] = app_models_module
    sys.modules["app.models.artifact"] = artifact_module
    sys.modules["app.models.process_step"] = process_step_module
    sys.modules["app.models.process_step_screenshot"] = screenshot_module
    sys.modules["app.models.process_step_screenshot_candidate"] = screenshot_candidate_module
    sys.modules["sqlalchemy"] = sqlalchemy_module
    sys.modules["worker"] = worker_module
    sys.modules["worker.bootstrap"] = bootstrap_module
    sys.modules["worker.services"] = services_module
    sys.modules["worker.pipeline.stages.stage_context"] = context_module
    sys.modules["worker.pipeline.types"] = generation_types_module

    spec = importlib.util.spec_from_file_location("screenshot_context_builder_test", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ScreenshotContextBuilderTests(unittest.TestCase):
    def test_raises_when_no_persisted_steps_exist(self) -> None:
        builder_module = load_builder_module()
        builder = builder_module.DefaultScreenshotContextBuilder()
        session = types.SimpleNamespace(
            id="session-1",
            artifacts=[types.SimpleNamespace(kind="transcript"), types.SimpleNamespace(kind="video")],
            process_steps=[],
            process_notes=[],
        )

        with self.assertRaisesRegex(ValueError, "No generated process steps"):
            builder.build(db=types.SimpleNamespace(), session=session)

    def test_removes_screenshot_evidence_and_resolves_transcript_id(self) -> None:
        builder_module = load_builder_module()
        builder = builder_module.DefaultScreenshotContextBuilder()
        step = types.SimpleNamespace(
            id="step-1",
            process_group_id="group-1",
            meeting_id="meeting-1",
            step_number=1,
            application_name="App",
            action_text="Click Save",
            source_data_note="",
            timestamp="00:00:05",
            start_timestamp="00:00:05",
            end_timestamp="00:00:06",
            supporting_transcript_text="Click Save",
            screenshot_id="old",
            confidence=0.9,
            evidence_references=json.dumps(
                [
                    {"kind": "transcript", "artifact_id": "tx-1"},
                    {"kind": "screenshot", "artifact_id": "ss-1"},
                ]
            ),
            edited_by_ba=False,
            source_transcript_artifact_id=None,
        )
        session = types.SimpleNamespace(
            id="session-1",
            artifacts=[
                types.SimpleNamespace(id="tx-1", kind="transcript", meeting_id="meeting-1", created_at=1),
                types.SimpleNamespace(id="vid-1", kind="video", meeting_id="meeting-1", created_at=1),
            ],
            process_steps=[step],
            process_notes=[],
        )
        db = types.SimpleNamespace(
            execute=lambda *args, **kwargs: None,
            commit=lambda: None,
        )

        context = builder.build(db=db, session=session)

        self.assertEqual(json.loads(step.evidence_references), [{"kind": "transcript", "artifact_id": "tx-1"}])
        self.assertEqual(context.all_steps[0]["_transcript_artifact_id"], "tx-1")
        self.assertEqual(context.persisted_step_models[0].id, "step-1")


if __name__ == "__main__":
    unittest.main()
