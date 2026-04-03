r"""
Purpose: AI-powered transcript-to-steps interpreter using an OpenAI-compatible API.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\ai_transcript_interpreter.py
"""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping, Sequence

from worker.bootstrap import get_backend_settings
from worker.services.ai_transcript.client import extract_content, parse_json_object, post_chat_completion
from worker.services.ai_transcript.diagrams import normalize_diagram_view
from worker.services.ai_transcript.models import (
    AmbiguousProcessGroupResolution,
    DiagramInterpretation,
    ProcessGroupInterpretation,
    ProcessSummaryInterpretation,
    TranscriptInterpretation,
    WorkflowBoundaryInterpretation,
    WorkflowCapabilityInterpretation,
    WorkflowGroupMatchInterpretation,
    WorkflowSemanticEnrichmentInterpretation,
    WorkflowTitleInterpretation,
)
from worker.services.ai_transcript.workflows import (
    classify_workflow_boundary as workflow_classify_workflow_boundary,
    classify_workflow_capabilities as workflow_classify_workflow_capabilities,
    enrich_workflow_segment as workflow_enrich_workflow_segment,
    infer_process_group as workflow_infer_process_group,
    match_existing_workflow_group as workflow_match_existing_workflow_group,
    resolve_ambiguous_process_group as workflow_resolve_ambiguous_process_group,
    resolve_workflow_title as workflow_resolve_workflow_title,
    summarize_process_group as workflow_summarize_process_group,
)
from worker.services.ai_transcript.normalization import (
    calibrate_confidence,
    confidence_from_rank,
    confidence_rank,
    normalize_confidence,
    normalize_existing_title,
    normalize_label,
    normalize_label_list,
    normalize_note,
    normalize_optional_text,
    normalize_slug,
    normalize_step,
    normalize_textish,
    normalize_timestamp,
    summary_quality_points,
    title_quality_points,
    workflow_evidence_points,
)
from worker.services.ai_skills.transcript_to_steps.schemas import TranscriptToStepsRequest, TranscriptToStepsResponse
from worker.services.ai_skills.transcript_to_steps.skill import TranscriptToStepsSkill
from worker.services.generation_types import NoteRecord, StepRecord

logger = logging.getLogger(__name__)


class AITranscriptInterpreter:
    """Interpret raw transcripts into structured process steps and business rules."""

    def __init__(self) -> None:
        self.settings = get_backend_settings()
        self._transcript_to_steps_skill = TranscriptToStepsSkill()

    def is_enabled(self) -> bool:
        """Return whether AI interpretation is configured."""
        return bool(self.settings.ai_enabled and self.settings.ai_api_key and self.settings.ai_base_url and self.settings.ai_model)

    def interpret(self, *, transcript_artifact_id: str, transcript_text: str) -> TranscriptInterpretation | None:
        """Call the configured AI provider and return structured transcript output."""
        if not self.is_enabled():
            return None
        logger.info(
            "Delegating transcript interpretation to AI skill.",
            extra={
                "skill_id": self._transcript_to_steps_skill.skill_id,
                "skill_version": self._transcript_to_steps_skill.version,
                "transcript_artifact_id": transcript_artifact_id,
            },
        )
        skill_result = self._transcript_to_steps_skill.run(
            TranscriptToStepsRequest(
                transcript_artifact_id=transcript_artifact_id,
                transcript_text=transcript_text,
            )
        )
        return self._build_legacy_transcript_interpretation(
            transcript_artifact_id=transcript_artifact_id,
            skill_result=skill_result,
        )

    def _build_legacy_transcript_interpretation(
        self,
        *,
        transcript_artifact_id: str,
        skill_result: TranscriptToStepsResponse,
    ) -> TranscriptInterpretation:
        """Adapt the first AI skill output back into the interpreter's legacy shape."""
        steps = [
            self._normalize_step(
                {
                    "application_name": item.application_name,
                    "action_text": item.action_text,
                    "source_data_note": item.source_data_note,
                    "start_timestamp": item.start_timestamp,
                    "end_timestamp": item.end_timestamp,
                    "display_timestamp": item.display_timestamp,
                    "supporting_transcript_text": item.supporting_transcript_text,
                    "confidence": item.confidence,
                },
                transcript_artifact_id,
            )
            for item in skill_result.steps
        ]
        notes = [
            self._normalize_note(
                {
                    "text": item.text,
                    "confidence": item.confidence,
                    "inference_type": item.inference_type,
                }
            )
            for item in skill_result.notes
        ]
        return TranscriptInterpretation(steps=steps, notes=notes)

    def interpret_diagrams(
        self,
        *,
        session_title: str,
        diagram_type: str,
        steps: Sequence[Mapping[str, Any]],
        notes: Sequence[Mapping[str, Any]],
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

    def infer_process_group(
        self,
        *,
        transcript_name: str,
        steps: Sequence[Mapping[str, Any]],
        notes: Sequence[Mapping[str, Any]],
        existing_titles: list[str],
    ) -> ProcessGroupInterpretation | None:
        """Infer a stable business process title and whether it matches an existing process group."""
        if not self.is_enabled():
            return None
        return workflow_infer_process_group(
            settings=self.settings,
            transcript_name=transcript_name,
            steps=steps,
            notes=notes,
            existing_titles=existing_titles,
        )

    def resolve_ambiguous_process_group(
        self,
        *,
        transcript_name: str,
        inferred_title: str,
        candidate_matches: Sequence[Mapping[str, Any]],
        steps: Sequence[Mapping[str, Any]],
        notes: Sequence[Mapping[str, Any]],
    ) -> AmbiguousProcessGroupResolution | None:
        """Use AI only for low-confidence process-group tie-break cases."""
        if not self.is_enabled():
            return None
        return workflow_resolve_ambiguous_process_group(
            settings=self.settings,
            transcript_name=transcript_name,
            inferred_title=inferred_title,
            candidate_matches=candidate_matches,
            steps=steps,
            notes=notes,
        )

    def resolve_workflow_title(
        self,
        *,
        transcript_name: str,
        workflow_summary: dict[str, Any],
    ) -> WorkflowTitleInterpretation | None:
        """Resolve a stable business workflow title from workflow signals."""
        if not self.is_enabled():
            return None
        return workflow_resolve_workflow_title(
            settings=self.settings,
            transcript_name=transcript_name,
            workflow_summary=workflow_summary,
        )

    def classify_workflow_boundary(
        self,
        *,
        left_segment: dict[str, Any],
        right_segment: dict[str, Any],
    ) -> WorkflowBoundaryInterpretation | None:
        """Classify whether adjacent evidence belongs to the same workflow."""
        if not self.is_enabled():
            return None
        return workflow_classify_workflow_boundary(
            settings=self.settings,
            left_segment=left_segment,
            right_segment=right_segment,
        )

    def match_existing_workflow_group(
        self,
        *,
        transcript_name: str,
        workflow_summary: dict[str, Any],
        existing_groups: list[dict[str, Any]],
    ) -> WorkflowGroupMatchInterpretation | None:
        """Match workflow evidence against existing workflow groups before heuristic fallback."""
        if not self.is_enabled():
            return None
        return workflow_match_existing_workflow_group(
            settings=self.settings,
            transcript_name=transcript_name,
            workflow_summary=workflow_summary,
            existing_groups=existing_groups,
        )

    def enrich_workflow_segment(
        self,
        *,
        segment_text: str,
        transcript_name: str | None = None,
        segment_context: dict[str, Any] | None = None,
    ) -> WorkflowSemanticEnrichmentInterpretation | None:
        """Extract workflow-relevant semantic labels from one evidence segment."""
        if not self.is_enabled():
            return None
        return workflow_enrich_workflow_segment(
            settings=self.settings,
            segment_text=segment_text,
            transcript_name=transcript_name,
            segment_context=segment_context,
        )

    def summarize_process_group(
        self,
        *,
        process_title: str,
        workflow_summary: dict[str, Any],
        steps: Sequence[Mapping[str, Any]],
        notes: Sequence[Mapping[str, Any]],
        document_type: str,
    ) -> ProcessSummaryInterpretation | None:
        """Generate a concise business summary for one resolved workflow/process group."""
        if not self.is_enabled():
            return None
        return workflow_summarize_process_group(
            settings=self.settings,
            process_title=process_title,
            workflow_summary=workflow_summary,
            steps=steps,
            notes=notes,
            document_type=document_type,
        )

    def classify_workflow_capabilities(
        self,
        *,
        process_title: str,
        workflow_summary: dict[str, Any],
        document_type: str,
    ) -> WorkflowCapabilityInterpretation | None:
        """Classify broader business capability tags without changing workflow identity."""
        if not self.is_enabled():
            return None
        return workflow_classify_workflow_capabilities(
            settings=self.settings,
            process_title=process_title,
            workflow_summary=workflow_summary,
            document_type=document_type,
        )

    @staticmethod
    def _extract_content(response_body: dict[str, Any]) -> str:
        """Extract message text from a chat completions response."""
        return extract_content(response_body)

    def _post_chat_completion(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        context: str,
    ) -> dict[str, Any]:
        """POST to the configured OpenAI-compatible endpoint and normalize retryable failures."""
        return post_chat_completion(
            timeout_seconds=self.settings.ai_timeout_seconds,
            endpoint=endpoint,
            headers=headers,
            payload=payload,
            context=context,
        )

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        """Parse JSON from the model response, even if wrapped in markdown fences."""
        return parse_json_object(text)

    @staticmethod
    def _normalize_step(item: Mapping[str, Any], transcript_artifact_id: str) -> StepRecord:
        """Normalize one AI-produced step into the worker's step shape."""
        return normalize_step(item, transcript_artifact_id)

    @staticmethod
    def _normalize_note(item: Mapping[str, Any]) -> NoteRecord:
        """Normalize one AI-produced note into the worker's note shape."""
        return normalize_note(item)

    @staticmethod
    def _normalize_confidence(value: Any) -> str:
        """Constrain confidence values to the supported enum."""
        return normalize_confidence(value)

    @classmethod
    def _calibrate_confidence(
        cls,
        confidence: str,
        *,
        evidence_points: int,
        quality_points: int,
        lower_when: int = 2,
    ) -> str:
        return calibrate_confidence(
            confidence,
            evidence_points=evidence_points,
            quality_points=quality_points,
            lower_when=lower_when,
        )

    @staticmethod
    def _confidence_rank(confidence: str) -> int:
        return confidence_rank(confidence)

    @staticmethod
    def _confidence_from_rank(rank: int) -> str:
        return confidence_from_rank(rank)

    @staticmethod
    def _workflow_evidence_points(workflow_summary: dict[str, Any]) -> int:
        return workflow_evidence_points(workflow_summary)

    @staticmethod
    def _title_quality_points(workflow_title: str) -> int:
        return title_quality_points(workflow_title)

    @staticmethod
    def _summary_quality_points(summary_text: str) -> int:
        return summary_quality_points(summary_text)

    @staticmethod
    def _normalize_slug(value: str, *, fallback: str) -> str:
        return normalize_slug(value, fallback=fallback)

    @staticmethod
    def _normalize_existing_title(value: str, *, existing_titles: list[str]) -> str | None:
        return normalize_existing_title(value, existing_titles=existing_titles)

    @staticmethod
    def _normalize_label(value: str) -> str:
        return normalize_label(value)

    @classmethod
    def _normalize_label_list(
        cls,
        values: Any,
        *,
        max_items: int,
        exclude: set[str] | None = None,
    ) -> list[str]:
        return normalize_label_list(values, max_items=max_items, exclude=exclude)

    @staticmethod
    def _normalize_textish(value: str) -> str:
        return normalize_textish(value)

    @staticmethod
    def _normalize_timestamp(value: str) -> str:
        """Normalize flexible transcript timestamps into HH:MM:SS."""
        return normalize_timestamp(value)

    @staticmethod
    def _normalize_diagram_view(view: dict[str, Any], view_type: str, session_title: str) -> dict[str, Any]:
        """Normalize one AI-produced diagram view into the API shape."""
        return normalize_diagram_view(view, view_type, session_title)

    @staticmethod
    def _normalize_optional_text(value: Any) -> str | None:
        """Normalize optional scalar text fields from AI output."""
        return normalize_optional_text(value)
