r"""Typed job message envelope (versioned, broker-agnostic wire contract for producers)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class JobType(StrEnum):
    """Stable job discriminator for `JobEnvelope` and non-Celery consumers."""

    DRAFT_GENERATION = "draft_generation"
    SCREENSHOT_GENERATION = "screenshot_generation"


class JobEnvelope(BaseModel):
    """Formal producer payload; JSON-serializable for SQS / HTTP bridges."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1, ge=1, description="Schema version for forward-compatible consumers.")
    job_type: JobType
    session_id: str = Field(min_length=1)
