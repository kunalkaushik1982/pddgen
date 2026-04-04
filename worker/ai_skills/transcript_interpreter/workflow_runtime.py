from __future__ import annotations

from typing import Any

from worker.ai_skills.transcript_interpreter.client import post_chat_completion


def post_json(*, settings: Any, payload: dict[str, Any], context: str) -> dict[str, Any]:
    endpoint = f"{settings.ai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
    }
    return post_chat_completion(
        timeout_seconds=settings.ai_timeout_seconds,
        endpoint=endpoint,
        headers=headers,
        payload=payload,
        context=context,
    )
