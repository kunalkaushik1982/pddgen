from __future__ import annotations

from typing import Any


def extract_message_content(response_body: dict[str, Any]) -> str:
    choices = response_body.get("choices", [])
    if not choices:
        raise ValueError("AI skill response did not contain any choices.")

    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, list):
        return "".join(item.get("text", "") for item in content if isinstance(item, dict))
    if isinstance(content, str):
        return content
    raise ValueError("AI skill response content was not in a supported format.")


class OpenAICompatibleSkillClient:
    def __init__(self) -> None:
        from worker.bootstrap import get_backend_settings

        self.settings = get_backend_settings()

    def is_enabled(self) -> bool:
        return bool(
            self.settings.ai_enabled
            and self.settings.ai_api_key
            and self.settings.ai_base_url
            and self.settings.ai_model
        )

    def post_json(self, *, messages: list[dict[str, str]], temperature: float = 0.1) -> dict[str, Any]:
        import httpx

        endpoint = f"{self.settings.ai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.ai_model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }
        timeout = httpx.Timeout(self.settings.ai_timeout_seconds)
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"AI skill request timed out after {self.settings.ai_timeout_seconds:.0f} seconds."
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(f"AI skill request failed with HTTP {status_code}.") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"AI skill request failed: {exc.__class__.__name__}.") from exc
