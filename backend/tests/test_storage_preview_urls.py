from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
import types
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "storage" / "storage_service.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def install_storage_stubs():
    app_module = types.ModuleType("app")
    app_module.__path__ = []  # type: ignore[attr-defined]
    core_module = types.ModuleType("app.core")
    config_module = types.ModuleType("app.core.config")
    boto3_module = types.ModuleType("boto3")
    botocore_module = types.ModuleType("botocore")
    client_module = types.ModuleType("botocore.client")
    fastapi_module = types.ModuleType("fastapi")

    @dataclass
    class FakeSettings:
        api_prefix: str = "/api"
        storage_backend: str = "local"
        local_storage_root: Path = Path("C:/tmp/storage")
        object_storage_bucket: str = "preview-bucket"
        object_storage_region: str = ""
        object_storage_endpoint_url: str = ""
        object_storage_access_key_id: str = ""
        object_storage_secret_access_key: str = ""
        object_storage_prefix: str = "pdd-generator"
        object_storage_addressing_style: str = "auto"
        preview_url_signing_secret: str = "preview-secret"
        preview_url_ttl_seconds: int = 900

    class FakeUploadFile:
        def __init__(self):
            self.file = types.SimpleNamespace(read=lambda: b"")

    class FakeBotoClient:
        def __init__(self):
            self.calls: list[tuple[str, object]] = []

        def generate_presigned_url(self, operation_name: str, Params: dict[str, object], ExpiresIn: int) -> str:
            self.calls.append((operation_name, Params))
            return f"https://cdn.example.test/{Params['Key']}?ttl={ExpiresIn}"

    fake_client = FakeBotoClient()

    config_module.Settings = FakeSettings
    config_module.get_settings = lambda: FakeSettings()
    boto3_module.client = lambda *args, **kwargs: fake_client
    client_module.Config = lambda *args, **kwargs: {"args": args, "kwargs": kwargs}
    fastapi_module.UploadFile = FakeUploadFile

    sys.modules["app"] = app_module
    sys.modules["app.core"] = core_module
    sys.modules["app.core.config"] = config_module
    sys.modules["boto3"] = boto3_module
    sys.modules["botocore"] = botocore_module
    sys.modules["botocore.client"] = client_module
    sys.modules["fastapi"] = fastapi_module

    return FakeSettings, fake_client


def load_storage_module():
    return load_module("storage_preview_urls_test", MODULE_PATH)


class StoragePreviewUrlTests(unittest.TestCase):
    def test_local_storage_preview_url_contains_signature_and_expiry(self) -> None:
        FakeSettings, _ = install_storage_stubs()
        module = load_storage_module()

        backend = module.LocalStorageBackend(FakeSettings())
        artifact = types.SimpleNamespace(
            id="artifact-1",
            name="step.png",
            storage_path="C:/tmp/storage/session/screenshots/step.png",
            content_type="image/png",
        )

        descriptor = backend.build_preview_descriptor(artifact, FakeSettings())

        self.assertIn("/api/uploads/artifacts/artifact-1/preview", descriptor.url)
        self.assertIn("expires=", descriptor.url)
        self.assertIn("sig=", descriptor.url)
        self.assertIsNotNone(descriptor.expires_at)

    def test_validate_preview_signature_accepts_valid_signature(self) -> None:
        FakeSettings, _ = install_storage_stubs()
        module = load_storage_module()
        service = module.StorageService(backend=module.LocalStorageBackend(FakeSettings()))
        expires = 4102444800
        signature = module._sign_preview_token(
            artifact_id="artifact-2",
            expires=expires,
            secret=FakeSettings().preview_url_signing_secret,
        )

        service.validate_preview_signature("artifact-2", expires, signature)

    def test_s3_storage_preview_url_uses_presigned_result(self) -> None:
        FakeSettings, fake_client = install_storage_stubs()
        module = load_storage_module()

        backend = module.S3CompatibleStorageBackend(FakeSettings(storage_backend="s3"))
        artifact = types.SimpleNamespace(
            id="artifact-3",
            name="step.png",
            storage_path="s3://preview-bucket/pdd-generator/session/screenshots/step.png",
            content_type="image/png",
        )

        descriptor = backend.build_preview_descriptor(artifact, FakeSettings(storage_backend="s3"))

        self.assertEqual(
            descriptor.url,
            "https://cdn.example.test/pdd-generator/session/screenshots/step.png?ttl=900",
        )
        self.assertEqual(fake_client.calls[0][0], "get_object")


if __name__ == "__main__":
    unittest.main()
