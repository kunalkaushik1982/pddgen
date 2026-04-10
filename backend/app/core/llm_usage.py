r"""
Purpose: Structured logging for OpenAI-compatible chat completion usage (tokens, model) per session.
Full filepath: backend/app/core/llm_usage.py
"""

from __future__ import annotations

import logging
from typing import Any


def log_chat_completion_usage(
    logger: logging.Logger,
    *,
    response_body: dict[str, Any],
    session_id: str | None,
    skill_id: str,
    model_requested: str | None = None,
) -> None:
    """Emit one log line with token usage from a /chat/completions JSON body."""
    usage = response_body.get("usage")
    if not isinstance(usage, dict):
        usage = {}
    response_model = response_body.get("model")
    model = response_model if isinstance(response_model, str) else model_requested

    extra = {
        "event": "llm.completion.usage",
        "session_id": session_id,
        "skill_id": skill_id,
        "model": model,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }
    logger.info("LLM completion usage", extra=extra)
