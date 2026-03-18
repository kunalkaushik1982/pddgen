r"""
Purpose: Identity provider registry and factory for configurable auth backends.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\auth_provider_registry.py
"""

from collections.abc import Callable

from app.core.config import Settings
from app.services.auth_types import IdentityProvider
from app.services.password_identity_provider import PasswordIdentityProvider


class UnsupportedPasswordMfaProvider:
    """Placeholder seam for future password+MFA providers."""

    provider_name = "password_mfa"

    def register(self, db, *, username: str, password: str):  # type: ignore[no-untyped-def]
        raise NotImplementedError(
            "Password+MFA auth provider is not configured yet. Supply an implementation behind auth_provider=password_mfa."
        )

    def authenticate(self, db, *, username: str, password: str):  # type: ignore[no-untyped-def]
        raise NotImplementedError(
            "Password+MFA auth provider is not configured yet. Supply an implementation behind auth_provider=password_mfa."
        )


class UnsupportedSsoIdentityProvider:
    """Placeholder seam for future enterprise SSO providers."""

    provider_name = "sso"

    def register(self, db, *, username: str, password: str):  # type: ignore[no-untyped-def]
        raise NotImplementedError("SSO auth providers do not support self-service registration in this implementation.")

    def authenticate(self, db, *, username: str, password: str):  # type: ignore[no-untyped-def]
        raise NotImplementedError(
            "SSO auth provider is not configured yet. Supply an implementation behind auth_provider=sso."
        )


ProviderFactory = Callable[[], IdentityProvider]


class AuthProviderRegistry:
    """Resolve the configured identity provider without changing route code."""

    def __init__(self) -> None:
        self._factories: dict[str, ProviderFactory] = {
            "password": PasswordIdentityProvider,
            "password_mfa": UnsupportedPasswordMfaProvider,
            "sso": UnsupportedSsoIdentityProvider,
        }

    def build(self, settings: Settings) -> IdentityProvider:
        factory = self._factories.get(settings.auth_provider)
        if factory is None:
            raise RuntimeError(f"Unsupported auth provider '{settings.auth_provider}'.")
        return factory()
