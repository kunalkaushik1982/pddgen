from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
import types
import typing
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "services" / "draft_session" / "mappers.py"

_MAPPER_STUB_KEYS = (
    "app",
    "app.api",
    "app.api.dependencies",
    "app.models",
    "app.models.artifact",
    "app.models.draft_session",
    "app.models.process_group",
    "app.models.process_note",
    "app.models.process_step",
    "app.models.process_step_screenshot_candidate",
    "app.models.process_step_screenshot",
    "app.schemas.common",
    "app.schemas.draft_session",
)
_mapper_stub_depth = 0
_mapper_stub_saved: dict[str, types.ModuleType | None] | None = None


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def install_mapper_stubs():
    global _mapper_stub_depth, _mapper_stub_saved
    if _mapper_stub_depth == 0:
        _mapper_stub_saved = {k: sys.modules.get(k) for k in _MAPPER_STUB_KEYS}
    _mapper_stub_depth += 1

    app_module = types.ModuleType("app")
    app_module.__path__ = []  # type: ignore[attr-defined]
    api_module = types.ModuleType("app.api")
    dependencies_module = types.ModuleType("app.api.dependencies")
    models_module = types.ModuleType("app.models")
    models_module.__path__ = []  # type: ignore[attr-defined]
    artifact_module = types.ModuleType("app.models.artifact")
    draft_session_module = types.ModuleType("app.models.draft_session")
    process_group_module = types.ModuleType("app.models.process_group")
    process_note_module = types.ModuleType("app.models.process_note")
    process_step_module = types.ModuleType("app.models.process_step")
    process_step_candidate_module = types.ModuleType("app.models.process_step_screenshot_candidate")
    process_step_screenshot_module = types.ModuleType("app.models.process_step_screenshot")
    schemas_common_module = types.ModuleType("app.schemas.common")
    schemas_draft_session_module = types.ModuleType("app.schemas.draft_session")

    class FakeStorageService:
        def build_preview_descriptor(self, artifact):
            return types.SimpleNamespace(
                url=f"/api/uploads/artifacts/{artifact.id}/preview?expires=1&sig=ok",
                expires_at="2030-01-01T00:00:00Z",
            )

    @dataclass
    class ArtifactResponse:
        id: str
        meeting_id: str | None = None
        upload_batch_id: str | None = None
        upload_pair_index: int | None = None
        name: str = ""
        kind: str = "screenshot"
        storage_path: str = ""
        content_type: str | None = None
        preview_url: str | None = None
        preview_expires_at: object | None = None
        size_bytes: int = 0
        created_at: object | None = None

    @dataclass
    class StepScreenshotResponse:
        id: str
        artifact_id: str
        role: str
        sequence_number: int
        timestamp: str
        selection_method: str
        is_primary: bool
        artifact: ArtifactResponse

    @dataclass
    class CandidateScreenshotResponse:
        id: str
        artifact_id: str
        sequence_number: int
        timestamp: str
        source_role: str
        selection_method: str
        is_selected: bool
        artifact: ArtifactResponse

    dependencies_module.get_storage_service = lambda: FakeStorageService()
    artifact_module.ArtifactModel = object
    draft_session_module.DraftSessionModel = object
    process_group_module.ProcessGroupModel = object
    process_note_module.ProcessNoteModel = object
    process_step_module.ProcessStepModel = object
    process_step_candidate_module.ProcessStepScreenshotCandidateModel = object
    process_step_screenshot_module.ProcessStepScreenshotModel = object
    schemas_common_module.EvidenceReference = types.SimpleNamespace(model_validate=lambda value: value)
    schemas_common_module.ArtifactKind = typing.Literal["video", "transcript", "template", "sop", "diagram", "screenshot"]
    schemas_common_module.ConfidenceLevel = typing.Literal["high", "medium", "low", "unknown"]
    schemas_common_module.WorkflowDocumentType = typing.Literal["pdd", "sop", "brd"]
    schemas_draft_session_module.ActionLogResponse = object
    schemas_draft_session_module.ArtifactResponse = ArtifactResponse
    schemas_draft_session_module.CandidateScreenshotResponse = CandidateScreenshotResponse
    schemas_draft_session_module.DraftSessionListItemResponse = object
    schemas_draft_session_module.DraftSessionResponse = object
    schemas_draft_session_module.PendingEvidenceBundleResponse = object
    schemas_draft_session_module.ProcessNoteResponse = object
    schemas_draft_session_module.ProcessGroupResponse = object
    schemas_draft_session_module.ProcessStepResponse = object
    schemas_draft_session_module.StepScreenshotResponse = StepScreenshotResponse

    class FakeOutputDocumentResponse:
        @staticmethod
        def model_validate(obj):
            return obj

    schemas_draft_session_module.OutputDocumentResponse = FakeOutputDocumentResponse

    sys.modules["app"] = app_module
    sys.modules["app.api"] = api_module
    sys.modules["app.api.dependencies"] = dependencies_module
    sys.modules["app.models"] = models_module
    sys.modules["app.models.artifact"] = artifact_module
    sys.modules["app.models.draft_session"] = draft_session_module
    sys.modules["app.models.process_group"] = process_group_module
    sys.modules["app.models.process_note"] = process_note_module
    sys.modules["app.models.process_step"] = process_step_module
    sys.modules["app.models.process_step_screenshot_candidate"] = process_step_candidate_module
    sys.modules["app.models.process_step_screenshot"] = process_step_screenshot_module
    sys.modules["app.schemas.common"] = schemas_common_module
    sys.modules["app.schemas.draft_session"] = schemas_draft_session_module


def _restore_mapper_stubs() -> None:
    global _mapper_stub_depth, _mapper_stub_saved
    if _mapper_stub_depth == 0:
        return
    _mapper_stub_depth -= 1
    if _mapper_stub_depth == 0 and _mapper_stub_saved is not None:
        for key, previous in _mapper_stub_saved.items():
            if previous is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = previous
        _mapper_stub_saved = None
    sys.modules.pop("artifact_preview_mapping_test", None)


def load_mapper_module():
    install_mapper_stubs()
    return load_module("artifact_preview_mapping_test", MODULE_PATH)


class ArtifactPreviewMappingTests(unittest.TestCase):
    def tearDown(self) -> None:
        while _mapper_stub_depth > 0:
            _restore_mapper_stubs()

    def test_map_step_screenshot_includes_preview_url(self) -> None:
        module = load_mapper_module()
        artifact = types.SimpleNamespace(
            id="artifact-1",
            meeting_id=None,
            upload_batch_id=None,
            upload_pair_index=None,
            name="step.png",
            kind="screenshot",
            storage_path="C:/tmp/step.png",
            content_type="image/png",
            size_bytes=10,
            created_at="2026-04-02T00:00:00Z",
        )
        step_screenshot = types.SimpleNamespace(
            id="step-shot-1",
            artifact_id="artifact-1",
            role="during",
            sequence_number=1,
            timestamp="00:00:05",
            selection_method="span-sequence",
            is_primary=True,
            artifact=artifact,
        )

        response = module.map_step_screenshot(step_screenshot)

        self.assertEqual(response.artifact.preview_url, "/api/uploads/artifacts/artifact-1/preview?expires=1&sig=ok")

    def test_map_candidate_screenshot_includes_preview_url(self) -> None:
        module = load_mapper_module()
        artifact = types.SimpleNamespace(
            id="artifact-2",
            meeting_id=None,
            upload_batch_id=None,
            upload_pair_index=None,
            name="candidate.png",
            kind="screenshot",
            storage_path="C:/tmp/candidate.png",
            content_type="image/png",
            size_bytes=10,
            created_at="2026-04-02T00:00:00Z",
        )
        candidate = types.SimpleNamespace(
            id="candidate-1",
            artifact_id="artifact-2",
            sequence_number=2,
            timestamp="00:00:07",
            source_role="during",
            selection_method="span-sequence",
            artifact=artifact,
        )

        response = module.map_candidate_screenshot(candidate, selected_artifact_ids=set())

        self.assertEqual(response.artifact.preview_url, "/api/uploads/artifacts/artifact-2/preview?expires=1&sig=ok")


if __name__ == "__main__":
    unittest.main()
