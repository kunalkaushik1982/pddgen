r"""
Purpose: AI-powered transcript-to-steps interpreter using an OpenAI-compatible API.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\ai_transcript_interpreter.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx

from worker.bootstrap import get_backend_settings

TIMESTAMP_PATTERN = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")


@dataclass
class TranscriptInterpretation:
    """Structured AI interpretation output."""

    steps: list[dict[str, Any]]
    notes: list[dict[str, Any]]


@dataclass
class DiagramInterpretation:
    """Structured AI diagram output."""

    overview: dict[str, Any]
    detailed: dict[str, Any]


class AITranscriptInterpreter:
    """Interpret raw transcripts into structured process steps and business rules."""

    def __init__(self) -> None:
        self.settings = get_backend_settings()

    def is_enabled(self) -> bool:
        """Return whether AI interpretation is configured."""
        return bool(self.settings.ai_enabled and self.settings.ai_api_key and self.settings.ai_base_url and self.settings.ai_model)

    def interpret(self, *, transcript_artifact_id: str, transcript_text: str) -> TranscriptInterpretation | None:
        """Call the configured AI provider and return structured transcript output."""
        if not self.is_enabled():
            return None

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You convert RPA discovery transcripts into structured process steps and business rules. "
                        "Return strict JSON with two keys: steps and notes. "
                        "Each step must include application_name, action_text, source_data_note, "
                        "start_timestamp, end_timestamp, display_timestamp, supporting_transcript_text, confidence. "
                        "Each note must include text, confidence, inference_type. "
                        "Ignore greetings, filler talk, and YouTube-style intros. "
                        "Prefer timestamps from the transcript when present. "
                        "Every returned timestamp must be in HH:MM:SS format. "
                        "If a step has no clear timestamp, return an empty string for that field. "
                        "supporting_transcript_text must contain the exact transcript snippet that supports the step. "
                        "display_timestamp should be the best single timestamp to show in UI and export. "
                        "Confidence must be one of high, medium, low, unknown."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Convert this transcript into process steps and business rules.\n\n"
                        f"Transcript:\n{transcript_text}"
                    ),
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        endpoint = f"{self.settings.ai_base_url.rstrip('/')}/chat/completions"

        body = self._post_chat_completion(endpoint=endpoint, headers=headers, payload=payload, context="transcript interpretation")

        content = self._extract_content(body)
        parsed = self._parse_json_object(content)
        steps = [self._normalize_step(item, transcript_artifact_id) for item in parsed.get("steps", [])]
        notes = [self._normalize_note(item) for item in parsed.get("notes", [])]
        return TranscriptInterpretation(steps=steps, notes=notes)

    def interpret_diagrams(
        self,
        *,
        session_title: str,
        diagram_type: str,
        steps: list[dict[str, Any]],
        notes: list[dict[str, Any]],
    ) -> DiagramInterpretation | None:
        """Call the configured AI provider and return structured overview and detailed diagram models."""
        if not self.is_enabled() or diagram_type.lower() != "flowchart":
            return None

        step_payload = [
            {
                "step_number": step.get("step_number"),
                "application_name": step.get("application_name", ""),
                "action_text": step.get("action_text", ""),
                "source_data_note": step.get("source_data_note", ""),
                "supporting_transcript_text": step.get("supporting_transcript_text", ""),
            }
            for step in steps
        ]
        note_payload = [
            {
                "text": note.get("text", ""),
                "inference_type": note.get("inference_type", ""),
                "confidence": note.get("confidence", ""),
            }
            for note in notes
        ]

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You convert discovered process steps into two flowchart graph models for a PDD. "
                        "Return strict JSON with exactly two keys: overview and detailed. "
                        "Each view must contain title, nodes, and edges. "
                        "Each node must contain id, label, category, step_range. "
                        "Each edge must contain id, source, target, label. "
                        "Allowed node categories are only process and decision. "
                        "Use only the discovered process evidence provided. "
                        "Do not invent correction nodes, retry nodes, merge nodes, helper nodes, or error-handling paths unless they are explicitly supported by the evidence. "
                        "Every node in each view must belong to one connected workflow. "
                        "Do not create isolated nodes. "
                        "Do not create disconnected subgraphs. "
                        "Every edge must reference valid node ids in the same view. "
                        "The graph must read as a coherent workflow from first node to last node. "
                        "Use category=decision only when the evidence explicitly describes a conditional branch or multiple possible outcomes, such as if/else, yes/no, whether X exists, approved/rejected, or pass/fail. "
                        "Do not classify simple actions as decision. "
                        "Actions such as open, enter, type, select, choose, save, submit, click, navigate, validate, check, and verify must remain process nodes unless the evidence explicitly describes branching or alternate outcomes. "
                        "Overview is a compact business summary of the same process. "
                        "Overview should prefer 5 to 9 nodes when possible. "
                        "Overview should group detailed steps into business-level phases, stay mostly linear, and include a decision node only when it is a major business branch that materially changes the flow. "
                        "Do not include low-level technical validations in overview unless they are a major business branch. "
                        "Detailed must preserve discovered business action order. "
                        "Detailed should use one node per evidence-backed business action or explicit decision point. "
                        "If the evidence does not clearly support branching, keep the detailed graph linear. "
                        "Use concise, professional business labels. "
                        "Do not repeat raw transcript wording unnecessarily. "
                        "Do not use vague labels like Process Step or Do Action. "
                        "Every node must include a valid step_range using the provided step numbers, such as Step 3 or Steps 4-6. "
                        "Example linear case: Open SAP -> Enter vendor number -> Enter material details -> Save purchase order. All nodes must be process nodes in one connected linear graph. "
                        "Example decision case: Check whether supplier exists -> If supplier does not exist, create supplier -> Continue purchase order creation. A decision node is allowed only because branching is explicit. "
                        "Do not return markdown. Return only valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "session_title": session_title,
                            "diagram_type": diagram_type,
                            "steps": step_payload,
                            "notes": note_payload,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        endpoint = f"{self.settings.ai_base_url.rstrip('/')}/chat/completions"

        body = self._post_chat_completion(endpoint=endpoint, headers=headers, payload=payload, context="diagram interpretation")

        content = self._extract_content(body)
        parsed = self._parse_json_object(content)
        overview = self._normalize_diagram_view(parsed.get("overview", {}), "overview", session_title)
        detailed = self._normalize_diagram_view(parsed.get("detailed", {}), "detailed", session_title)
        return DiagramInterpretation(overview=overview, detailed=detailed)

    @staticmethod
    def _extract_content(response_body: dict[str, Any]) -> str:
        """Extract message text from a chat completions response."""
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

    def _post_chat_completion(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        context: str,
    ) -> dict[str, Any]:
        """POST to the configured OpenAI-compatible endpoint and normalize retryable failures."""
        timeout = httpx.Timeout(self.settings.ai_timeout_seconds)
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"AI {context} timed out after {self.settings.ai_timeout_seconds:.0f} seconds."
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(f"AI {context} failed with HTTP {status_code}.") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"AI {context} request failed: {exc.__class__.__name__}.") from exc

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        """Parse JSON from the model response, even if wrapped in markdown fences."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        return json.loads(cleaned)

    @staticmethod
    def _normalize_step(item: dict[str, Any], transcript_artifact_id: str) -> dict[str, Any]:
        """Normalize one AI-produced step into the worker's step shape."""
        start_timestamp = AITranscriptInterpreter._normalize_timestamp(str(item.get("start_timestamp", "") or ""))
        end_timestamp = AITranscriptInterpreter._normalize_timestamp(str(item.get("end_timestamp", "") or ""))
        display_timestamp = AITranscriptInterpreter._normalize_timestamp(
            str(item.get("display_timestamp", item.get("timestamp", "")) or "")
        )
        supporting_transcript_text = str(item.get("supporting_transcript_text", "") or "").strip()
        locator = display_timestamp or start_timestamp or "ai:transcript"
        return {
            "step_number": 0,
            "application_name": str(item.get("application_name", "") or ""),
            "action_text": str(item.get("action_text", "") or "").strip(),
            "source_data_note": str(item.get("source_data_note", "") or "").strip(),
            "timestamp": display_timestamp,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "supporting_transcript_text": supporting_transcript_text,
            "screenshot_id": "",
            "confidence": AITranscriptInterpreter._normalize_confidence(item.get("confidence")),
            "evidence_references": json.dumps(
                [
                    {
                        "id": str(uuid4()),
                        "artifact_id": transcript_artifact_id,
                        "kind": "transcript",
                        "locator": locator,
                    }
                ]
            ),
            "edited_by_ba": False,
        }

    @staticmethod
    def _normalize_note(item: dict[str, Any]) -> dict[str, Any]:
        """Normalize one AI-produced note into the worker's note shape."""
        return {
            "text": str(item.get("text", "") or "").strip(),
            "related_step_ids": json.dumps([]),
            "evidence_reference_ids": json.dumps([]),
            "confidence": AITranscriptInterpreter._normalize_confidence(item.get("confidence")),
            "inference_type": str(item.get("inference_type", "inferred") or "inferred"),
        }

    @staticmethod
    def _normalize_confidence(value: Any) -> str:
        """Constrain confidence values to the supported enum."""
        normalized = str(value or "medium").lower()
        return normalized if normalized in {"high", "medium", "low", "unknown"} else "medium"

    @staticmethod
    def _normalize_timestamp(value: str) -> str:
        """Normalize flexible transcript timestamps into HH:MM:SS."""
        if not value:
            return ""

        match = TIMESTAMP_PATTERN.search(value.strip())
        if not match:
            return ""

        hours_group, minutes_group, seconds_group = match.groups()
        hours = int(hours_group or 0)
        minutes = int(minutes_group)
        seconds = int(seconds_group)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _normalize_diagram_view(view: dict[str, Any], view_type: str, session_title: str) -> dict[str, Any]:
        """Normalize one AI-produced diagram view into the API shape."""
        raw_nodes = view.get("nodes", []) if isinstance(view, dict) else []
        raw_edges = view.get("edges", []) if isinstance(view, dict) else []

        nodes: list[dict[str, str]] = []
        node_ids: set[str] = set()
        for index, item in enumerate(raw_nodes, start=1):
            node_id = str(item.get("id", "") or f"{view_type}_n{index}").strip()
            if not node_id or node_id in node_ids:
                node_id = f"{view_type}_n{index}"
            node_ids.add(node_id)
            category = str(item.get("category", "process") or "process").strip().lower()
            if category not in {"process", "decision"}:
                category = "process"
            nodes.append(
                {
                    "id": node_id,
                    "label": str(item.get("label", "") or "").strip() or f"Step {index}",
                    "category": category,
                    "step_range": str(item.get("step_range", "") or "").strip(),
                }
            )

        edges: list[dict[str, str]] = []
        for index, item in enumerate(raw_edges, start=1):
            source = str(item.get("source", "") or "").strip()
            target = str(item.get("target", "") or "").strip()
            if source not in node_ids or target not in node_ids:
                continue
            edges.append(
                {
                    "id": str(item.get("id", "") or f"{view_type}_e{index}").strip() or f"{view_type}_e{index}",
                    "source": source,
                    "target": target,
                    "label": str(item.get("label", "") or "").strip(),
                }
            )

        if not nodes:
            nodes = [{"id": f"{view_type}_n1", "label": "No process steps available", "category": "process", "step_range": ""}]
            edges = []

        return {
            "diagram_type": "flowchart",
            "view_type": view_type,
            "title": str(view.get("title", "") or session_title).strip() or session_title,
            "nodes": nodes,
            "edges": edges,
        }
