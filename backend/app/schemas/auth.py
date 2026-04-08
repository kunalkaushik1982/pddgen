r"""
Purpose: API schemas for user authentication and session identity.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\schemas\auth.py
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuthRequest(BaseModel):
    """Username/password payload for login or registration."""

    username: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=4, max_length=255)


class GoogleAuthRequest(BaseModel):
    """Google ID token payload for sign-in/up via Google Identity Services."""

    id_token: str = Field(min_length=20)


class PasswordResetRequest(BaseModel):
    """Start password reset for a username/email."""

    username: str = Field(min_length=3, max_length=255)


class PasswordResetConfirmRequest(BaseModel):
    """Finalize password reset with one-time token."""

    token: str = Field(min_length=16, max_length=512)
    new_password: str = Field(min_length=4, max_length=255)


class PasswordResetRequestResponse(BaseModel):
    accepted: bool = True
    reset_token: str | None = None


class UserResponse(BaseModel):
    """Authenticated user response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    created_at: datetime
    is_admin: bool = False


class AuthResponse(BaseModel):
    """Authenticated user and any next-step auth metadata."""

    auth_status: str = "authenticated"
    challenge_type: str | None = None
    challenge_token: str | None = None
    token: str | None = None
    user: UserResponse
