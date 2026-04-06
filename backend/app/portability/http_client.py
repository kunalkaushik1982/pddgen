r"""
Shared HTTP client factory for OpenAI-compatible chat endpoints.

Inject the returned `httpx.Client` into `SessionGroundedQASkill` (and similar) from
`dependencies.py` to centralize timeouts, proxies, or custom TLS without changing Q&A logic.
"""

from __future__ import annotations

import httpx

from app.core.config import Settings


def build_llm_http_client(settings: Settings) -> httpx.Client:
    """Long-timeout client for LLM HTTP APIs (OpenAI-compatible by default)."""
    return httpx.Client(timeout=httpx.Timeout(settings.ai_timeout_seconds))
