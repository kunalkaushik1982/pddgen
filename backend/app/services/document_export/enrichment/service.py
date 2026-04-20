r"""
One chat completion that returns JSON ``fields`` for the requested placeholder keys only.

Invoked from the draft-generation worker after diagram assembly, before persistence.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.llm_usage import log_chat_completion_usage
from app.core.observability import bind_log_context, get_logger
from app.services.admin.usage_metrics_service import persist_llm_usage_from_response_body_standalone
from app.services.document_export.enrichment.instructions import load_field_instruction

logger = get_logger(__name__)


def _extract_message_content(response_body: dict[str, Any]) -> str:
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


SKILL_ID = "document_export_text_enrichment"


class DocumentExportEnrichmentService:
    """Batched LLM enrichment for export template placeholders."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_enabled(self) -> bool:
        return bool(
            self.settings.ai_enabled
            and self.settings.ai_document_export_enrichment_enabled
            and self.settings.ai_api_key
            and self.settings.ai_base_url
            and self.settings.ai_model
        )

    def run(
        self,
        *,
        evidence_digest: str,
        session_id: str,
        field_ids: tuple[str, ...],
    ) -> dict[str, str] | None:
        """Return field_id -> polished text for ``field_ids`` only, or None if skipped/failed."""
        if not self.is_enabled():
            return None
        if not field_ids:
            logger.info(
                "Document export enrichment skipped (no fields for document type).",
                extra={"event": "document_export_enrichment.no_fields"},
            )
            return None
        system, user = self._build_messages(evidence_digest, field_ids)
        with bind_log_context(session_id=session_id):
            try:
                body = self._post_chat(system=system, user=user, session_id=session_id)
            except Exception as exc:
                logger.warning(
                    "Document export enrichment failed; export will use deterministic text.",
                    extra={"event": "document_export_enrichment.failed", "error": str(exc)},
                )
                return None
        try:
            content = _extract_message_content(body)
            data: Any = json.loads(content)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Document export enrichment returned invalid JSON.",
                extra={"event": "document_export_enrichment.invalid_json", "error": str(exc)},
            )
            return None
        return self._coerce_fields(data, field_ids)

    def _build_messages(self, evidence_digest: str, field_ids: tuple[str, ...]) -> tuple[str, str]:
        keys_list = ", ".join(f'"{k}"' for k in field_ids)
        system = (
            "You are a senior business analyst improving export-ready narrative text for process documentation. "
            "You MUST respond with a single JSON object only (no markdown fences). "
            f'The object MUST have a key "fields" whose value is an object with exactly these string keys: {keys_list}. '
            "Each value must be a concise, professional paragraph (or short list converted to prose) suitable for Word. "
            "Ground every statement in the evidence; do not invent systems, people, or metrics not supported by the evidence. "
            "If evidence is thin, write shorter text rather than speculating."
        )
        parts: list[str] = [
            "## Session evidence (ground truth)\n",
            evidence_digest,
            "\n## Field-specific writing instructions\n",
        ]
        for fid in field_ids:
            instr = load_field_instruction(fid)
            if instr:
                parts.append(f"### {fid}\n{instr}\n\n")
            else:
                parts.append(f"### {fid}\n(Polish a clear narrative appropriate for this field.)\n\n")
        user = "".join(parts)
        return system, user

    def _post_chat(self, *, system: str, user: str, session_id: str) -> dict[str, Any]:
        endpoint = f"{self.settings.ai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.25,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        timeout = httpx.Timeout(self.settings.ai_timeout_seconds)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        log_chat_completion_usage(
            logger,
            response_body=body,
            session_id=session_id,
            skill_id=SKILL_ID,
            model_requested=self.settings.ai_model,
        )
        persist_llm_usage_from_response_body_standalone(
            session_id=session_id,
            skill_id=SKILL_ID,
            response_body=body,
        )
        return body

    def _coerce_fields(self, data: Any, field_ids: tuple[str, ...]) -> dict[str, str] | None:
        if not isinstance(data, dict):
            return None
        raw_fields = data.get("fields")
        if not isinstance(raw_fields, dict):
            return None
        out: dict[str, str] = {}
        for fid in field_ids:
            val = raw_fields.get(fid)
            if isinstance(val, str) and val.strip():
                out[fid] = val.strip()
        return out if out else None
