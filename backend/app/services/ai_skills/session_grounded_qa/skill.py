from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from app.core.observability import get_logger
from app.services.ai_skills.session_grounded_qa.schemas import (
    SessionGroundedQARequest,
    SessionGroundedQAResponse,
)

logger = get_logger(__name__)


def load_markdown_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def extract_message_content(response_body: dict[str, Any]) -> str:
    choices = response_body.get("choices", [])
    if not choices:
        raise RuntimeError("Ask this Session did not receive any model choices.")
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, list):
        return "".join(item.get("text", "") for item in content if isinstance(item, dict))
    if isinstance(content, str):
        return content
    raise RuntimeError("Ask this Session returned content in an unsupported format.")


def normalize_confidence(value: Any) -> str:
    normalized = str(value or "medium").lower()
    return normalized if normalized in {"high", "medium", "low"} else "medium"


def normalize_citation_ids(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    citation_ids: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        citation_ids.append(cleaned)
    return citation_ids


class SessionGroundedQASkill:
    skill_id = "session_grounded_qa"
    version = "1.0"

    def __init__(self, *, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self._client = client

    def build_messages(self, request: SessionGroundedQARequest) -> list[dict[str, str]]:
        prompt_text = load_markdown_text(Path(__file__).with_name("prompt.md"))
        return [
            {"role": "system", "content": prompt_text},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "session_title": request.session_title,
                        "process_group_id": request.process_group_id,
                        "question": request.question,
                        "evidence": request.evidence,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def run(self, input: SessionGroundedQARequest) -> SessionGroundedQAResponse:
        logger.info(
            "Executing AI skill.",
            extra={
                "skill_id": self.skill_id,
                "skill_version": self.version,
                "process_group_id": input.process_group_id,
            },
        )
        body = self._post_chat_completion(
            endpoint=f"{self.settings.ai_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.ai_api_key}",
                "Content-Type": "application/json",
            },
            payload={
                "model": self.settings.ai_model,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": self.build_messages(input),
            },
        )
        parsed = parse_json_object(extract_message_content(body))
        return SessionGroundedQAResponse(
            answer=str(parsed.get("answer", "") or "").strip(),
            confidence=normalize_confidence(parsed.get("confidence")),
            citation_ids=normalize_citation_ids(parsed.get("citation_ids", [])),
        )

    def _post_chat_completion(self, *, endpoint: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
        timeout = httpx.Timeout(self.settings.ai_timeout_seconds)
        try:
            if self._client is None:
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(endpoint, headers=headers, json=payload)
            else:
                response = self._client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"Ask this Session timed out after {self.settings.ai_timeout_seconds:.0f} seconds.") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(f"Ask this Session failed with HTTP {status_code}.") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ask this Session request failed: {exc.__class__.__name__}.") from exc
