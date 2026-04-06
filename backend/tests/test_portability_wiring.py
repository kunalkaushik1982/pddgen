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


if __name__ == "__main__":
    unittest.main()
