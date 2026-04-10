from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "api" / "routes" / "uploads.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def install_route_stubs():
    app_module = types.ModuleType("app")
    app_module.__path__ = []  # type: ignore[attr-defined]
    api_module = types.ModuleType("app.api")
    dependencies_module = types.ModuleType("app.api.dependencies")
    db_module = types.ModuleType("app.db")
    db_session_module = types.ModuleType("app.db.session")
    models_module = types.ModuleType("app.models")
    models_module.__path__ = []  # type: ignore[attr-defined]
    user_module = types.ModuleType("app.models.user")
    artifact_module = types.ModuleType("app.models.artifact")
    schemas_common_module = types.ModuleType("app.schemas.common")
    schemas_draft_session_module = types.ModuleType("app.schemas.draft_session")
    services_module = types.ModuleType("app.services")
    services_module.__path__ = []  # type: ignore[attr-defined]
    artifact_ingestion_module = types.ModuleType("app.services.artifact_ingestion")
    action_log_module = types.ModuleType("app.services.action_log_service")
    mappers_module = types.ModuleType("app.services.mappers")
    meeting_service_module = types.ModuleType("app.services.meeting_service")
    process_group_service_module = types.ModuleType("app.services.process_group_service")
    storage_pkg = types.ModuleType("app.storage")
    storage_pkg.__path__ = []  # type: ignore[attr-defined]
    storage_service_module = types.ModuleType("app.storage.storage_service")
    fastapi_module = types.ModuleType("fastapi")
    responses_module = types.ModuleType("fastapi.responses")
    sqlalchemy_module = types.ModuleType("sqlalchemy")
    orm_module = types.ModuleType("sqlalchemy.orm")

    class APIRouter:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def post(self, *args, **kwargs):
            return lambda fn: fn

        def get(self, *args, **kwargs):
            return lambda fn: fn

        def delete(self, *args, **kwargs):
            return lambda fn: fn

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class Response:
        def __init__(self, status_code: int = 200, media_type: str | None = None, headers: dict[str, str] | None = None):
            self.status_code = status_code
            self.media_type = media_type
            self.headers = headers or {}

    class StreamingResponse(Response):
        def __init__(self, body, media_type: str | None = None, headers: dict[str, str] | None = None):
            super().__init__(status_code=200, media_type=media_type, headers=headers)
            self.body = body

    fastapi_module.APIRouter = APIRouter
    fastapi_module.Depends = lambda dependency: dependency
    fastapi_module.File = lambda *args, **kwargs: None
    fastapi_module.Form = lambda *args, **kwargs: None
    fastapi_module.HTTPException = HTTPException
    fastapi_module.Response = Response
    fastapi_module.UploadFile = object
    fastapi_module.status = types.SimpleNamespace(
        HTTP_200_OK=200,
        HTTP_201_CREATED=201,
        HTTP_204_NO_CONTENT=204,
        HTTP_403_FORBIDDEN=403,
        HTTP_404_NOT_FOUND=404,
    )
    responses_module.StreamingResponse = StreamingResponse
    orm_module.Session = object

    dependencies_module.get_action_log_service = lambda: None
    dependencies_module.get_artifact_ingestion_service = lambda: None
    dependencies_module.require_workspace_user = lambda: None
    dependencies_module.get_meeting_service = lambda: None
    dependencies_module.get_process_group_service = lambda: None
    dependencies_module.get_storage_service = lambda: None
    db_session_module.get_db_session = lambda: None
    user_module.UserModel = object
    artifact_module.ArtifactModel = object
    schemas_common_module.ArtifactKind = str
    schemas_draft_session_module.ArtifactResponse = object
    schemas_draft_session_module.CreateDraftSessionRequest = object
    schemas_draft_session_module.DraftSessionResponse = object
    artifact_ingestion_module.ArtifactIngestionService = object
    meeting_service_module.MeetingService = object
    process_group_service_module.ProcessGroupService = object

    class ActionLogService:
        def record(self, *args, **kwargs):
            return None

    action_log_module.ActionLogService = ActionLogService
    mappers_module.map_draft_session = lambda session: session
    storage_service_module.StorageService = object

    sys.modules["app"] = app_module
    sys.modules["app.api"] = api_module
    sys.modules["app.api.dependencies"] = dependencies_module
    sys.modules["app.db"] = db_module
    sys.modules["app.db.session"] = db_session_module
    sys.modules["app.models"] = models_module
    sys.modules["app.models.user"] = user_module
    sys.modules["app.models.artifact"] = artifact_module
    sys.modules["app.schemas.common"] = schemas_common_module
    sys.modules["app.schemas.draft_session"] = schemas_draft_session_module
    sys.modules["app.services"] = services_module
    sys.modules["app.services.artifact_ingestion"] = artifact_ingestion_module
    sys.modules["app.services.action_log_service"] = action_log_module
    sys.modules["app.services.mappers"] = mappers_module
    sys.modules["app.services.meeting_service"] = meeting_service_module
    sys.modules["app.services.process_group_service"] = process_group_service_module
    sys.modules["app.storage"] = storage_pkg
    sys.modules["app.storage.storage_service"] = storage_service_module
    sys.modules["fastapi"] = fastapi_module
    sys.modules["fastapi.responses"] = responses_module
    sys.modules["sqlalchemy"] = sqlalchemy_module
    sys.modules["sqlalchemy.orm"] = orm_module


def load_route_module():
    install_route_stubs()
    return load_module("artifact_preview_route_test", MODULE_PATH)


class ArtifactPreviewRouteTests(unittest.TestCase):
    def test_preview_route_streams_bytes_when_internal_redirect_is_unavailable(self) -> None:
        module = load_route_module()

        artifact = types.SimpleNamespace(id="artifact-2", name="step.png", storage_path="C:/tmp/step.png", content_type="image/png")
        db = types.SimpleNamespace(get=lambda model, artifact_id: artifact)
        storage_service = types.SimpleNamespace(
            validate_preview_signature=lambda artifact_id, expires, signature: None,
            build_internal_artifact_path=lambda storage_path: None,
            read_bytes=lambda storage_path: b"image-bytes",
        )

        response = module.get_artifact_preview(
            artifact_id="artifact-2",
            expires=4102444800,
            sig="valid",
            db=db,
            storage_service=storage_service,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "image/png")
        self.assertFalse("X-Accel-Redirect" in response.headers)

    def test_preview_route_serves_signed_local_artifact(self) -> None:
        module = load_route_module()

        artifact = types.SimpleNamespace(id="artifact-1", name="step.png", storage_path="C:/tmp/step.png", content_type="image/png")
        db = types.SimpleNamespace(get=lambda model, artifact_id: artifact)
        storage_service = types.SimpleNamespace(
            validate_preview_signature=lambda artifact_id, expires, signature: None,
            build_internal_artifact_path=lambda storage_path: "/_protected-artifacts/session/step.png",
            read_bytes=lambda storage_path: b"image-bytes",
        )

        response = module.get_artifact_preview(
            artifact_id="artifact-1",
            expires=4102444800,
            sig="valid",
            db=db,
            storage_service=storage_service,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "image/png")
        self.assertEqual(response.headers["X-Accel-Redirect"], "/_protected-artifacts/session/step.png")

    def test_preview_route_rejects_invalid_signature(self) -> None:
        module = load_route_module()

        db = types.SimpleNamespace(get=lambda model, artifact_id: None)
        storage_service = types.SimpleNamespace(
            validate_preview_signature=lambda artifact_id, expires, signature: (_ for _ in ()).throw(RuntimeError("Invalid preview signature.")),
            build_internal_artifact_path=lambda storage_path: None,
            read_bytes=lambda storage_path: b"",
        )

        with self.assertRaises(module.HTTPException) as context:
            module.get_artifact_preview(
                artifact_id="artifact-1",
                expires=4102444800,
                sig="bad",
                db=db,
                storage_service=storage_service,
            )

        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(context.exception.detail, "Invalid preview signature.")


if __name__ == "__main__":
    unittest.main()
