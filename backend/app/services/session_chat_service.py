r"""
Purpose: Grounded session Q&A over transcript, steps, and notes using an OpenAI-compatible API.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\session_chat_service.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.models.draft_session import DraftSessionModel
from app.storage.storage_service import StorageService


@dataclass
class SessionEvidenceItem:
    """Grounding unit used for session Q&A."""

    evidence_id: str
    source_type: str
    title: str
    content: str
    snippet: str


class SessionChatService:
    """Answer grounded questions about one session."""

    def __init__(self, storage_service: StorageService | None = None) -> None:
        self.settings = get_settings()
        self.storage_service = storage_service or StorageService()

    def is_enabled(self) -> bool:
        """Return whether AI-backed session chat is configured."""
        return bool(self.settings.ai_enabled and self.settings.ai_api_key and self.settings.ai_base_url and self.settings.ai_model)

    def ask(self, *, session: DraftSessionModel, question: str, process_group_id: str | None = None) -> dict[str, Any]:
        """Return one grounded answer with citations for the provided session question."""
        if not self.is_enabled():
            raise RuntimeError("Ask this Session is unavailable because AI is not configured.")

        cleaned_question = question.strip()
        if not cleaned_question:
            raise RuntimeError("A question is required.")

        evidence_items = self._build_evidence_items(session, process_group_id=process_group_id)
        if not evidence_items:
            raise RuntimeError("No grounded session evidence is available yet for this question.")

        evidence_payload = [
            {
                "id": item.evidence_id,
                "source_type": item.source_type,
                "title": item.title,
                "content": item.content,
            }
            for item in evidence_items
        ]

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You answer business analyst questions about one recorded session. "
                        "Use only the supplied evidence. "
                        "Do not invent facts. "
                        "If the evidence is insufficient, say so directly. "
                        "Return strict JSON with keys answer, confidence, and citation_ids. "
                        "answer must be concise and business-readable. "
                        "confidence must be one of high, medium, low. "
                        "citation_ids must be an array of evidence ids actually used in the answer."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "session_title": session.title,
                            "process_group_id": process_group_id,
                            "question": cleaned_question,
                            "evidence": evidence_payload,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }

        endpoint = f"{self.settings.ai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        body = self._post_chat_completion(endpoint=endpoint, headers=headers, payload=payload)
        content = self._extract_content(body)
        parsed = self._parse_json_object(content)

        cited_ids = [str(item) for item in parsed.get("citation_ids", []) if str(item).strip()]
        evidence_by_id = {item.evidence_id: item for item in evidence_items}
        citations = [
            {
                "id": cited_id,
                "source_type": evidence_by_id[cited_id].source_type,
                "title": evidence_by_id[cited_id].title,
                "snippet": evidence_by_id[cited_id].snippet,
            }
            for cited_id in cited_ids
            if cited_id in evidence_by_id
        ]

        return {
            "answer": str(parsed.get("answer", "") or "").strip() or "The session evidence did not support a confident answer.",
            "confidence": self._normalize_confidence(parsed.get("confidence")),
            "citations": citations,
        }

    def _build_evidence_items(self, session: DraftSessionModel, *, process_group_id: str | None = None) -> list[SessionEvidenceItem]:
        """Build a bounded set of evidence items for model grounding."""
        evidence_items: list[SessionEvidenceItem] = []

        filtered_steps = [
            step
            for step in sorted(session.process_steps, key=lambda item: item.step_number)
            if process_group_id is None or step.process_group_id == process_group_id
        ]
        filtered_notes = [
            note
            for note in session.process_notes
            if process_group_id is None or note.process_group_id == process_group_id
        ]
        allowed_meeting_ids = {step.meeting_id for step in filtered_steps if step.meeting_id} | {
            note.meeting_id for note in filtered_notes if note.meeting_id
        }

        for step in filtered_steps:
            step_body_parts = [
                f"Application: {step.application_name}" if step.application_name else "",
                f"Action: {step.action_text}" if step.action_text else "",
                f"Source data: {step.source_data_note}" if step.source_data_note else "",
                f"Timestamp: {step.timestamp}" if step.timestamp else "",
                f"Transcript evidence: {step.supporting_transcript_text}" if step.supporting_transcript_text else "",
            ]
            step_body = " | ".join(part for part in step_body_parts if part)
            if not step_body:
                continue
            evidence_items.append(
                SessionEvidenceItem(
                    evidence_id=f"step-{step.step_number}",
                    source_type="step",
                    title=f"Step {step.step_number}",
                    content=step_body,
                    snippet=self._truncate(step_body, 220),
                )
            )

        for index, note in enumerate(filtered_notes[:8], start=1):
            note_body = note.text.strip()
            if not note_body:
                continue
            evidence_items.append(
                SessionEvidenceItem(
                    evidence_id=f"note-{index}",
                    source_type="note",
                    title=f"Business note {index}",
                    content=note_body,
                    snippet=self._truncate(note_body, 220),
                )
            )

        transcript_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "transcript"]
        if process_group_id is not None and allowed_meeting_ids:
            transcript_artifacts = [
                artifact for artifact in transcript_artifacts if getattr(artifact, "meeting_id", None) in allowed_meeting_ids
            ]
        transcript_chunk_index = 1
        for artifact in transcript_artifacts[:3]:
            transcript_text = self.storage_service.read_text(artifact.storage_path).strip()
            if not transcript_text:
                continue
            for chunk in self._chunk_text(transcript_text, chunk_size=1400, max_chunks=4):
                evidence_items.append(
                    SessionEvidenceItem(
                        evidence_id=f"transcript-{transcript_chunk_index}",
                        source_type="transcript",
                        title=artifact.name,
                        content=chunk,
                        snippet=self._truncate(chunk.replace("\n", " "), 240),
                    )
                )
                transcript_chunk_index += 1

        return evidence_items[:20]

    def _post_chat_completion(self, *, endpoint: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
        """POST to the configured OpenAI-compatible chat completions endpoint."""
        timeout = httpx.Timeout(self.settings.ai_timeout_seconds)
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"Ask this Session timed out after {self.settings.ai_timeout_seconds:.0f} seconds.") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(f"Ask this Session failed with HTTP {status_code}.") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ask this Session request failed: {exc.__class__.__name__}.") from exc

    @staticmethod
    def _extract_content(response_body: dict[str, Any]) -> str:
        """Extract message text from a chat completions response."""
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

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        """Parse a JSON object, tolerating markdown fences."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        return json.loads(cleaned)

    @staticmethod
    def _normalize_confidence(value: Any) -> str:
        """Constrain confidence values to the supported chat enum."""
        normalized = str(value or "medium").lower()
        return normalized if normalized in {"high", "medium", "low"} else "medium"

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        """Return a short readable snippet."""
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."

    @staticmethod
    def _chunk_text(text: str, *, chunk_size: int, max_chunks: int) -> list[str]:
        """Chunk long transcript text into bounded segments."""
        normalized = text.strip()
        if not normalized:
            return []
        chunks: list[str] = []
        cursor = 0
        while cursor < len(normalized) and len(chunks) < max_chunks:
            next_cursor = min(len(normalized), cursor + chunk_size)
            chunks.append(normalized[cursor:next_cursor])
            cursor = next_cursor
        return chunks
