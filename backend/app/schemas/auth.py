r"""
Purpose: API schemas for user authentication and session identity.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\schemas\auth.py
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AuthRequest(BaseModel):
    """Username/password payload for login."""

    username: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=4, max_length=255)


class RegisterRequest(BaseModel):
    """Self-service registration with a reachable email for verification and password reset."""

    username: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=4, max_length=255)
    email: EmailStr


class GoogleAuthRequest(BaseModel):
    """Google token payload for sign-in/up via Google Identity Services."""

    id_token: str | None = Field(default=None, min_length=20)
    access_token: str | None = Field(default=None, min_length=20)


class PasswordResetRequest(BaseModel):
    """Start password reset for a verified account email."""

    email: EmailStr


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
    email: str | None = None
    email_verified: bool = False
    created_at: datetime
    is_admin: bool = False
    admin_console_only: bool = False
    billing_gstin: str | None = None
    billing_legal_name: str | None = None
    billing_state_code: str | None = None


class AuthResponse(BaseModel):
    """Authenticated user and any next-step auth metadata."""

    auth_status: str = "authenticated"
    challenge_type: str | None = None
    challenge_token: str | None = None
    token: str | None = None
    user: UserResponse
