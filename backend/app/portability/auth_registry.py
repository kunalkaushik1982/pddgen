r"""
Auth provider registry with optional plug-in factories from another module.

Set `auth_provider_extensions_module` in Settings (env: PDD_GENERATOR_AUTH_PROVIDER_EXTENSIONS_MODULE)
to a dotted import path. That module must define::

    AUTH_PROVIDER_FACTORIES: dict[str, Callable[[], IdentityProvider]]

Keys are provider names; values are zero-arg factories returning an IdentityProvider.
"""

from __future__ import annotations

import importlib

from app.core.config import Settings
from app.services.auth_provider_registry import AuthProviderRegistry, ProviderFactory
from app.services.auth_types import IdentityProvider


class ExtensibleAuthProviderRegistry(AuthProviderRegistry):
    """Built-in providers plus optional factories merged from an extension module."""

    def __init__(self, extra_factories: dict[str, ProviderFactory] | None = None) -> None:
        super().__init__()
        if extra_factories:
            for key, factory in extra_factories.items():
                if not key or not callable(factory):
                    raise RuntimeError(f"Invalid auth provider extension entry for key {key!r}.")
            self._factories.update(extra_factories)


def _load_extension_factories(settings: Settings) -> dict[str, ProviderFactory]:
    module_name = (getattr(settings, "auth_provider_extensions_module", None) or "").strip()
    if not module_name:
        return {}
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise RuntimeError(
            f"Could not import auth_provider_extensions_module={module_name!r}. "
            "Fix the module path or clear the setting."
        ) from exc
    raw = getattr(module, "AUTH_PROVIDER_FACTORIES", None)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise RuntimeError(
            f"Module {module_name!r} must define AUTH_PROVIDER_FACTORIES as a dict[str, factory]."
        )
    out: dict[str, ProviderFactory] = {}
    for key, factory in raw.items():
        sk = str(key).strip()
        if not sk or not callable(factory):
            raise RuntimeError(f"Invalid AUTH_PROVIDER_FACTORIES entry for key {key!r}.")
        out[sk] = factory  # type: ignore[assignment]
    return out


def build_auth_provider_registry(settings: Settings) -> AuthProviderRegistry:
    """Return a registry: defaults plus optional extension module (plug-and-play auth)."""
    extra = _load_extension_factories(settings)
    if not extra:
        return AuthProviderRegistry()
    return ExtensibleAuthProviderRegistry(extra)


def build_identity_provider(settings: Settings) -> IdentityProvider:
    """Convenience: configured IdentityProvider instance."""
    return build_auth_provider_registry(settings).build(settings)
