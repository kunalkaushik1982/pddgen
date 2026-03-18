r"""
Purpose: Auth domain types and extension interfaces for backend authentication.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\auth_types.py
"""

from dataclasses import dataclass
from typing import Literal, Protocol

from sqlalchemy.orm import Session

from app.models.user import UserModel


AuthStatus = Literal["authenticated", "challenge_required"]


@dataclass(slots=True)
class AuthSession:
    """Represent one authenticated backend session."""

    user: UserModel
    session_token: str
    status: AuthStatus = "authenticated"
    challenge_type: str | None = None
    challenge_token: str | None = None


class IdentityProvider(Protocol):
    """Authenticate or register users through one identity mechanism."""

    provider_name: str

    def register(self, db: Session, *, username: str, password: str) -> UserModel:
        """Create one new identity and return the associated user."""

    def authenticate(self, db: Session, *, username: str, password: str) -> UserModel:
        """Authenticate one identity and return the associated user."""


class SessionService(Protocol):
    """Persist and resolve authenticated backend sessions."""

    def create_session(self, db: Session, *, user: UserModel) -> str:
        """Create one session token for the given user."""

    def revoke_session(self, db: Session, *, token: str) -> None:
        """Revoke one active session token."""

    def resolve_user(self, db: Session, *, token: str) -> UserModel:
        """Resolve one user from the provided session token."""
