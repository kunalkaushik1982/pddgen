from __future__ import annotations

import json
from typing import Any

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    httpx = None


def extract_content(response_body: dict[str, Any]) -> str:
    choices = response_body.get("choices", [])
    if not choices:
        raise ValueError("AI response did not contain any choices.")
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, list):
        return "".join(item.get("text", "") for item in content if isinstance(item, dict))
    if isinstance(content, str):
        return content
    raise ValueError("AI response content was not in a supported format.")


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def post_chat_completion(
    *,
    timeout_seconds: float,
    endpoint: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    context: str,
) -> dict[str, Any]:
    if httpx is None:
        raise RuntimeError("AI HTTP client dependency 'httpx' is not installed.")
    timeout = httpx.Timeout(timeout_seconds)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
            from app.core.llm_usage import log_chat_completion_usage
            from app.core.observability import get_log_context, get_logger

            ctx = get_log_context()
            sid = ctx.get("session_id") if isinstance(ctx, dict) else None
            log_chat_completion_usage(
                get_logger(__name__),
                response_body=body,
                session_id=sid,
                skill_id=f"transcript_interpreter:{context}",
                model_requested=payload.get("model") if isinstance(payload.get("model"), str) else None,
            )
            from app.services.admin.usage_metrics_service import persist_llm_usage_from_response_body_standalone

            persist_llm_usage_from_response_body_standalone(
                session_id=sid if isinstance(sid, str) else None,
                skill_id=f"transcript_interpreter:{context}",
                response_body=body,
            )
            return body
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"AI {context} timed out after {timeout_seconds:.0f} seconds.") from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        raise RuntimeError(f"AI {context} failed with HTTP {status_code}.") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"AI {context} request failed: {exc.__class__.__name__}.") from exc
