r"""
Purpose: Application settings for the backend service.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\core\config.py
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
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
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/pdd_generator",
        description=(
            "SQLAlchemy URL. Default is PostgreSQL (psycopg). For MySQL install the optional "
            "``mysql`` extra and use e.g. ``mysql+pymysql://user:pass@host:3306/db``."
        ),
    )
    database_pool_pre_ping: bool = Field(
        default=True,
        description="Enable SQLAlchemy pool_pre_ping for resilient connections across DB engines.",
    )
    redis_url: str = "redis://localhost:6379/0"
    lock_redis_url: str | None = Field(
        default=None,
        description="Optional Redis URL for distributed locks only; defaults to redis_url when unset.",
    )
    job_enqueue_backend: Literal["celery", "sqs", "azure_service_bus", "gcp_pubsub"] = Field(
        default="celery",
        description=(
            "Producer: celery (send_task), sqs (SendMessage), azure_service_bus (queue), "
            "gcp_pubsub (topic publish)."
        ),
    )
    job_enqueue_max_retries: int = Field(
        default=0,
        ge=0,
        description="Producer retry count on enqueue failures (per adapter send call).",
    )
    job_enqueue_retry_backoff_seconds: float = Field(
        default=0.5,
        ge=0.0,
        description="Base backoff seconds for producer retries (exponential per attempt).",
    )
    sqs_job_queue_url: str = Field(
        default="",
        description="SQS queue URL when job_enqueue_backend=sqs.",
    )
    sqs_job_queue_urls: dict[str, str] = Field(
        default_factory=dict,
        description="Optional logical queue -> SQS queue URL map; falls back to sqs_job_queue_url.",
    )
    sqs_is_fifo_queue: bool = Field(
        default=False,
        description="Set true for FIFO queues (adds MessageGroupId / MessageDeduplicationId).",
    )
    sqs_region: str | None = Field(
        default=None,
        description="Optional AWS region for the SQS client (else standard boto3 resolution).",
    )
    azure_service_bus_connection_string: str = Field(
        default="",
        description="Azure Service Bus namespace connection string when job_enqueue_backend=azure_service_bus.",
    )
    azure_service_bus_queue_name: str = Field(
        default="",
        description="Target queue name within the namespace for Azure Service Bus.",
    )
    azure_service_bus_queue_names: dict[str, str] = Field(
        default_factory=dict,
        description="Optional logical queue -> Azure Service Bus queue name map; falls back to azure_service_bus_queue_name.",
    )
    gcp_pubsub_project_id: str = Field(
        default="",
        description="GCP project ID when job_enqueue_backend=gcp_pubsub.",
    )
    gcp_pubsub_topic_id: str = Field(
        default="",
        description="Pub/Sub topic ID (not full path) when job_enqueue_backend=gcp_pubsub.",
    )
    gcp_pubsub_topic_ids: dict[str, str] = Field(
        default_factory=dict,
        description="Optional logical queue -> GCP Pub/Sub topic ID map; falls back to gcp_pubsub_topic_id.",
    )
    job_enqueue_factory: str = Field(
        default="",
        description=(
            "Optional plug-in: ``dotted.module.path:callable`` returning ``JobEnqueuePort`` given ``Settings``. "
            "When set, this overrides ``job_enqueue_backend`` (built-in registry is not used). "
            "Only use trusted module paths."
        ),
    )
    auth_provider: str = "password"
    auth_google_enabled: bool = False
    auth_google_client_id: str = ""
    auth_google_auto_create_user: bool = True
    auth_password_reset_enabled: bool = True
    auth_password_reset_token_ttl_minutes: int = 30
    auth_password_reset_return_token_in_response: bool = False
    auth_public_app_url: str = Field(
        default="http://localhost:5173",
        description="Public frontend base URL (no trailing slash). Used in password-reset emails.",
    )
    auth_api_public_base_url: str = Field(
        default="http://localhost:8000",
        description="Public backend base URL (no trailing slash). Used for /api/auth/verify-email links in mail.",
    )
    smtp_host: str = Field(
        default="",
        description="SMTP server hostname. When empty, verification emails are skipped (email auto-verified on register in dev).",
    )
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = Field(default="", description="RFC5322 From address; defaults to smtp_user if empty.")
    smtp_use_tls: bool = True
    auth_email_verification_token_ttl_minutes: int = Field(
        default=2880,
        ge=15,
        description="Time-to-live for email verification tokens (default 48 hours).",
    )
    auth_provider_extensions_module: str = Field(
        default="",
        description=(
            "Optional dotted module path exporting AUTH_PROVIDER_FACTORIES for extra IdentityProvider "
            "plug-ins without editing core registry code."
        ),
    )
    auth_session_backend: str = "database_token"
    auth_registration_enabled: bool = True
    admin_usernames: list[str] = Field(
        default_factory=lambda: ["admin"],
        description="Usernames that may access /api/admin/* and the Admin UI.",
    )
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
    ai_model: str = "gpt-4o"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: float = 180.0
    # OpenAI standard API pricing for gpt-4o (per 1M tokens on platform.openai.com/docs/pricing): $2.50 in, $10 out.
    ai_prompt_usd_per_1k_tokens: float = Field(default=0.0025, description="USD per 1k prompt tokens (gpt-4o: 2.50/1M).")
    ai_completion_usd_per_1k_tokens: float = Field(default=0.01, description="USD per 1k completion tokens (gpt-4o: 10/1M).")
    usd_to_inr_rate: float = Field(
        default=83.0,
        ge=0.0,
        description="Multiply USD estimates by this to show INR in admin (update to live FX as needed).",
    )
    admin_ai_cost_margin_multiplier: float = Field(
        default=1.5,
        ge=1.0,
        description="Display charge in INR = actual INR × this (1.5 = cost plus 50% margin).",
    )
    admin_processing_inr_per_minute_draft: float = Field(
        default=0.5,
        ge=0.0,
        description="Estimated INR cost per minute for draft_generation worker compute.",
    )
    admin_processing_inr_per_minute_screenshot: float = Field(
        default=0.35,
        ge=0.0,
        description="Estimated INR cost per minute for screenshot_generation worker compute.",
    )
    admin_storage_inr_per_gb_month: float = Field(
        default=2.0,
        ge=0.0,
        description="Estimated INR storage cost per GB-month used for admin cost rollups.",
    )
    admin_storage_retention_days: float = Field(
        default=30.0,
        ge=0.0,
        description="Retention window in days applied to per-session storage cost estimate.",
    )
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
    draft_generation_lock_seconds: int = Field(
        default=3600,
        description="TTL for draft-generation dedupe lock (API reserve until worker releases).",
    )
    screenshot_celery_soft_time_limit_seconds: float = Field(
        default=300.0,
        description="Celery soft time limit for screenshot_generation tasks (SIGUSR1-style SoftTimeLimitExceeded).",
    )
    screenshot_celery_time_limit_seconds: float = Field(
        default=330.0,
        description="Hard Celery time limit for screenshot_generation tasks (worker kills the job).",
    )
    draft_celery_soft_time_limit_seconds: float = Field(
        default=3600.0,
        description="Celery soft time limit for draft_generation tasks.",
    )
    draft_celery_time_limit_seconds: float = Field(
        default=3720.0,
        description="Hard Celery time limit for draft_generation tasks.",
    )
    screenshot_extraction_stale_after_seconds: float = Field(
        default=300.0,
        description=(
            "If latest 'Extracting screenshots' stage log is older than this, API lists the run as stalled for UX."
        ),
    )

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_prefix="PDD_GENERATOR_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_job_enqueue_backend(self) -> Self:
        if self.auth_google_enabled and not self.auth_google_client_id.strip():
            raise ValueError("auth_google_client_id is required when auth_google_enabled is true")
        if self.auth_password_reset_token_ttl_minutes <= 0:
            raise ValueError("auth_password_reset_token_ttl_minutes must be > 0")
        factory = self.job_enqueue_factory.strip()
        if factory:
            if ":" not in factory or factory.count(":") != 1:
                raise ValueError("job_enqueue_factory must be exactly 'module.path:callable'")
            module_path, attr = factory.split(":", 1)
            if not module_path.strip() or not attr.strip():
                raise ValueError("job_enqueue_factory must be exactly 'module.path:callable'")
            return self
        backend = self.job_enqueue_backend.strip().lower()
        if backend == "sqs" and not (self.sqs_job_queue_url.strip() or self.sqs_job_queue_urls):
            raise ValueError(
                "Configure sqs_job_queue_url or sqs_job_queue_urls when job_enqueue_backend is 'sqs'"
            )
        if backend == "azure_service_bus":
            if not self.azure_service_bus_connection_string.strip():
                raise ValueError(
                    "azure_service_bus_connection_string is required when job_enqueue_backend is 'azure_service_bus'"
                )
            if not (self.azure_service_bus_queue_name.strip() or self.azure_service_bus_queue_names):
                raise ValueError(
                    "Configure azure_service_bus_queue_name or azure_service_bus_queue_names "
                    "when job_enqueue_backend is 'azure_service_bus'"
                )
        if backend == "gcp_pubsub":
            if not self.gcp_pubsub_project_id.strip():
                raise ValueError("gcp_pubsub_project_id is required when job_enqueue_backend is 'gcp_pubsub'")
            if not (self.gcp_pubsub_topic_id.strip() or self.gcp_pubsub_topic_ids):
                raise ValueError(
                    "Configure gcp_pubsub_topic_id or gcp_pubsub_topic_ids when job_enqueue_backend is 'gcp_pubsub'"
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    settings = Settings()
    settings_release = get_release_info()
    settings.app_name = f"{settings.app_name} v{settings_release['backend']}"
    return settings
