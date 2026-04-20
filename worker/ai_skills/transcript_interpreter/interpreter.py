from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

from worker.bootstrap import get_backend_settings
from worker.ai_skills.transcript_to_steps.schemas import TranscriptToStepsRequest, TranscriptToStepsResponse
from worker.ai_skills.transcript_to_steps.skill import TranscriptToStepsSkill
from worker.ai_skills.transcript_interpreter.client import extract_content, parse_json_object, post_chat_completion
from worker.ai_skills.transcript_interpreter.diagram_interpreter import interpret_diagrams as ai_interpret_diagrams
from worker.ai_skills.transcript_interpreter.diagrams import normalize_diagram_view
from worker.ai_skills.transcript_interpreter.models import (
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
from worker.ai_skills.transcript_interpreter.normalization import (
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
from worker.ai_skills.transcript_interpreter.transcript_adaptation import build_legacy_transcript_interpretation
from worker.ai_skills.transcript_interpreter.workflows import (
    classify_workflow_boundary as workflow_classify_workflow_boundary,
    classify_workflow_capabilities as workflow_classify_workflow_capabilities,
    enrich_workflow_segment as workflow_enrich_workflow_segment,
    infer_process_group as workflow_infer_process_group,
    match_existing_workflow_group as workflow_match_existing_workflow_group,
    resolve_ambiguous_process_group as workflow_resolve_ambiguous_process_group,
    resolve_workflow_title as workflow_resolve_workflow_title,
    summarize_process_group as workflow_summarize_process_group,
)
from worker.pipeline.types import NoteRecord, StepRecord

logger = logging.getLogger(__name__)


class AITranscriptInterpreter:
    """Interpret raw transcripts into structured process steps and business rules."""

    def __init__(self) -> None:
        self.settings = get_backend_settings()
        self._transcript_to_steps_skill = TranscriptToStepsSkill()

    def is_enabled(self) -> bool:
        return bool(self.settings.ai_enabled and self.settings.ai_api_key and self.settings.ai_base_url and self.settings.ai_model)

    def interpret(
        self,
        *,
        transcript_artifact_id: str,
        transcript_text: str,
        max_steps: int | None = None,
    ) -> TranscriptInterpretation | None:
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
                max_steps=max_steps,
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
        return build_legacy_transcript_interpretation(
            transcript_artifact_id=transcript_artifact_id,
            skill_result=skill_result,
        )

    def interpret_diagrams(
        self,
        *,
        session_title: str,
        diagram_type: str,
        steps: Sequence[Mapping[str, Any]],
        notes: Sequence[Mapping[str, Any]],
    ) -> DiagramInterpretation | None:
        if not self.is_enabled() or diagram_type.lower() != "flowchart":
            return None
        return ai_interpret_diagrams(
            settings=self.settings,
            session_title=session_title,
            diagram_type=diagram_type,
            steps=steps,
            notes=notes,
        )

    def infer_process_group(self, *, transcript_name: str, steps: Sequence[Mapping[str, Any]], notes: Sequence[Mapping[str, Any]], existing_titles: list[str]) -> ProcessGroupInterpretation | None:
        if not self.is_enabled():
            return None
        return workflow_infer_process_group(settings=self.settings, transcript_name=transcript_name, steps=steps, notes=notes, existing_titles=existing_titles)

    def resolve_ambiguous_process_group(
        self,
        *,
        transcript_name: str,
        inferred_title: str,
        candidate_matches: Sequence[Mapping[str, Any]],
        steps: Sequence[Mapping[str, Any]],
        notes: Sequence[Mapping[str, Any]],
    ) -> AmbiguousProcessGroupResolution | None:
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

    def resolve_workflow_title(self, *, transcript_name: str, workflow_summary: dict[str, Any]) -> WorkflowTitleInterpretation | None:
        if not self.is_enabled():
            return None
        return workflow_resolve_workflow_title(settings=self.settings, transcript_name=transcript_name, workflow_summary=workflow_summary)

    def classify_workflow_boundary(self, *, left_segment: dict[str, Any], right_segment: dict[str, Any]) -> WorkflowBoundaryInterpretation | None:
        if not self.is_enabled():
            return None
        return workflow_classify_workflow_boundary(settings=self.settings, left_segment=left_segment, right_segment=right_segment)

    def match_existing_workflow_group(
        self,
        *,
        transcript_name: str,
        workflow_summary: dict[str, Any],
        existing_groups: list[dict[str, Any]],
    ) -> WorkflowGroupMatchInterpretation | None:
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
        return extract_content(response_body)

    def _post_chat_completion(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        context: str,
    ) -> dict[str, Any]:
        return post_chat_completion(
            timeout_seconds=self.settings.ai_timeout_seconds,
            endpoint=endpoint,
            headers=headers,
            payload=payload,
            context=context,
        )

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        return parse_json_object(text)

    @staticmethod
    def _normalize_step(item: Mapping[str, Any], transcript_artifact_id: str) -> StepRecord:
        return normalize_step(item, transcript_artifact_id)

    @staticmethod
    def _normalize_note(item: Mapping[str, Any]) -> NoteRecord:
        return normalize_note(item)

    @staticmethod
    def _normalize_confidence(value: Any) -> str:
        return normalize_confidence(value)

    @classmethod
    def _calibrate_confidence(cls, confidence: str, *, evidence_points: int, quality_points: int, lower_when: int = 2) -> str:
        return calibrate_confidence(confidence, evidence_points=evidence_points, quality_points=quality_points, lower_when=lower_when)

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

    @staticmethod
    def _normalize_label_list(values: Any, *, max_items: int, exclude: set[str] | None = None) -> list[str]:
        return normalize_label_list(values, max_items=max_items, exclude=exclude)

    @staticmethod
    def _normalize_textish(value: str) -> str:
        return normalize_textish(value)

    @staticmethod
    def _normalize_timestamp(value: str) -> str:
        return normalize_timestamp(value)

    @staticmethod
    def _normalize_diagram_view(view: dict[str, Any], view_type: str, session_title: str) -> dict[str, Any]:
        return normalize_diagram_view(view, view_type, session_title)

    @staticmethod
    def _normalize_optional_text(value: Any) -> str | None:
        return normalize_optional_text(value)
