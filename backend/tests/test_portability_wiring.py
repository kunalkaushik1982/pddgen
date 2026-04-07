"""Smoke tests for portability wiring (no database required)."""

from __future__ import annotations

import unittest

from app.core.config import Settings
from app.portability.auth_registry import build_auth_provider_registry, build_identity_provider
from app.services.auth_provider_registry import AuthProviderRegistry


class PortabilityAuthRegistryTests(unittest.TestCase):
    def test_default_registry_without_extensions_is_builtin(self) -> None:
        settings = Settings(
            database_url="postgresql+psycopg://x:x@localhost:5432/x",
            auth_provider_extensions_module="",
        )
        registry = build_auth_provider_registry(settings)
        self.assertIsInstance(registry, AuthProviderRegistry)
        self.assertIs(type(registry), AuthProviderRegistry)

    def test_identity_provider_builds_for_password(self) -> None:
        settings = Settings(
            database_url="postgresql+psycopg://x:x@localhost:5432/x",
            auth_provider="password",
            auth_provider_extensions_module="",
        )
        provider = build_identity_provider(settings)
        self.assertEqual(provider.provider_name, "password")


class JobEnqueueFactoryTests(unittest.TestCase):
    def test_dotted_factory_resolves_to_celery_adapter(self) -> None:
        from app.portability.job_messaging.enqueue_producers.celery_enqueue import CeleryJobEnqueueAdapter
        from app.portability.job_messaging.wiring import build_job_enqueue_port

        settings = Settings(
            database_url="postgresql+psycopg://x:x@localhost:5432/x",
            job_enqueue_factory="app.portability.job_messaging.wiring:_build_celery_enqueue",
        )
        port = build_job_enqueue_port(settings)
        self.assertIsInstance(port, CeleryJobEnqueueAdapter)


if __name__ == "__main__":
    unittest.main()
