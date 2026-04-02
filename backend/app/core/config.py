r"""
Purpose: Application settings for the backend service.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\core\config.py
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.release import get_release_info


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORAGE_ROOT = PROJECT_ROOT / "storage" / "local"


class Settings(BaseSettings):
    """Environment-backed configuration for the backend service."""

    app_name: str = "BA Process Copilot API"
    app_env: str = "development"
    app_debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pdd_generator"
    redis_url: str = "redis://localhost:6379/0"
    auth_provider: str = "password"
    auth_session_backend: str = "database_token"
    auth_registration_enabled: bool = True
    admin_usernames: list[str] = Field(default_factory=list)
    auth_token_days: int = 7
    auth_cookie_name: str = "pdd_generator_session"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    auth_cookie_domain: str | None = None
    auth_csrf_protection_enabled: bool = True
    auth_csrf_cookie_name: str = "pdd_generator_csrf"
    auth_csrf_header_name: str = "X-CSRF-Token"
    ai_enabled: bool = False
    ai_provider: str = "openai_compatible"
    ai_api_key: str = ""
    ai_model: str = "gpt-4.1-mini"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: float = 180.0
    storage_backend: str = "local"
    local_storage_root: Path = Field(default=DEFAULT_STORAGE_ROOT)
    object_storage_bucket: str = ""
    object_storage_region: str = ""
    object_storage_endpoint_url: str = ""
    object_storage_access_key_id: str = ""
    object_storage_secret_access_key: str = ""
    object_storage_prefix: str = "pdd-generator"
    object_storage_addressing_style: str = "auto"
    protected_artifact_internal_redirect_enabled: bool = False
    preview_url_signing_secret: str = "local-preview-secret"
    preview_url_ttl_seconds: int = 900
    max_upload_size_mb: int = 1024
    docx_output_folder: str = "exports"
    default_meeting_title_prefix: str = "Meeting"
    default_process_group_title_prefix: str = "Process"
    screenshot_candidate_count: int = 5
    screenshot_selected_count: int = 3
    screenshot_anchor_padding_seconds: int = 1
    screenshot_window_max_seconds: int = 45
    screenshot_short_window_seconds: int = 3
    screenshot_medium_window_seconds: int = 8
    screenshot_long_window_seconds: int = 20
    screenshot_anchor_candidate_cap: int = 5
    screenshot_short_window_candidate_cap: int = 3
    screenshot_medium_window_candidate_cap: int = 5
    screenshot_long_window_candidate_cap: int = 7
    screenshot_extended_window_candidate_cap: int = 9
    screenshot_ffmpeg_timeout_seconds: float = 8.0
    screenshot_generation_lock_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_prefix="PDD_GENERATOR_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    settings = Settings()
    settings_release = get_release_info()
    settings.app_name = f"{settings.app_name} v{settings_release['backend']}"
    return settings
