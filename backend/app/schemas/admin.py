r"""
Purpose: API schemas for admin visibility over users and jobs.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\schemas\admin.py
"""

from datetime import datetime

from pydantic import BaseModel, Field


class AdminUserListItemResponse(BaseModel):
    """Compact admin-visible user summary."""

    id: str
    username: str
    created_at: datetime
    is_admin: bool
    total_jobs: int
    active_jobs: int
    quota_lifetime_bonus: int = 0
    quota_daily_bonus: int = 0
    job_usage_lifetime: int = 0
    job_usage_daily: int = 0
    effective_lifetime_cap: int = 0
    effective_daily_cap: int = 0


class AdminUserQuotaUpdateRequest(BaseModel):
    """Adjust per-user quota bonuses added on top of global env defaults."""

    quota_lifetime_bonus: int | None = Field(default=None, ge=0)
    quota_daily_bonus: int | None = Field(default=None, ge=0)


class AdminSessionMetricsResponse(BaseModel):
    """Per-session rollups for LLM usage, processing time, and estimated costs."""

    session_id: str
    title: str
    owner_id: str
    status: str
    updated_at: datetime
    llm_call_count: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens_reported: int | None
    estimated_cost_usd: float | None
    actual_ai_cost_inr: float | None
    charge_inr_with_margin: float | None
    processing_cost_inr: float
    storage_bytes_total: int
    storage_cost_inr: float
    total_estimated_cost_inr: float
    draft_generation_seconds_total: float
    draft_generation_runs: int
    screenshot_generation_seconds_total: float
    screenshot_generation_runs: int


class AdminPreferencesResponse(BaseModel):
    """Admin console UI preferences persisted per user."""

    session_metrics_visible_columns: list[str] = Field(default_factory=list)
    metrics_selected_owner_id: str | None = None


class AdminPreferencesUpdateRequest(BaseModel):
    """Mutable admin console UI preferences."""

    session_metrics_visible_columns: list[str] = Field(default_factory=list)
    metrics_selected_owner_id: str | None = None


class MetricsOwnerOptionResponse(BaseModel):
    """Owner option available in the metrics scope selector."""

    id: str
    label: str
