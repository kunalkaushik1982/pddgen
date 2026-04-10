r"""
Purpose: API schemas for admin visibility over users and jobs.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\schemas\admin.py
"""

from datetime import datetime

from pydantic import BaseModel


class AdminUserListItemResponse(BaseModel):
    """Compact admin-visible user summary."""

    id: str
    username: str
    created_at: datetime
    is_admin: bool
    total_jobs: int
    active_jobs: int


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
