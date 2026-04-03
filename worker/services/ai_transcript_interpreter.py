r"""
Purpose: AI-powered transcript-to-steps interpreter using an OpenAI-compatible API.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\ai_transcript_interpreter.py
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from uuid import uuid4

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - dependency-light test environments
    httpx = None

from worker.bootstrap import get_backend_settings
from worker.services.ai_skills.transcript_to_steps.schemas import TranscriptToStepsRequest, TranscriptToStepsResponse
from worker.services.ai_skills.transcript_to_steps.skill import TranscriptToStepsSkill
from worker.services.generation_types import NoteRecord, StepRecord

TIMESTAMP_PATTERN = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")
logger = logging.getLogger(__name__)


@dataclass
class TranscriptInterpretation:
    """Structured AI interpretation output."""

    steps: list[StepRecord]
    notes: list[NoteRecord]


@dataclass
class DiagramInterpretation:
    """Structured AI diagram output."""

    overview: dict[str, Any]
    detailed: dict[str, Any]


@dataclass
class ProcessGroupInterpretation:
    """Structured process-group classification output."""

    process_title: str
    canonical_slug: str
    matched_existing_title: str | None


@dataclass
class AmbiguousProcessGroupResolution:
    """Structured AI tie-break result for ambiguous process-group resolution."""

    matched_existing_title: str | None
    recommended_title: str
    recommended_slug: str
    confidence: str
    rationale: str


@dataclass
class WorkflowTitleInterpretation:
    """Structured AI workflow-title resolution output."""

    workflow_title: str
    canonical_slug: str
    confidence: str
    rationale: str


@dataclass
class WorkflowBoundaryInterpretation:
    """Structured AI workflow-boundary classification output."""

    decision: str
    confidence: str
    rationale: str


@dataclass
class WorkflowGroupMatchInterpretation:
    """Structured AI workflow-group matching output."""

    matched_existing_title: str | None
    recommended_title: str
    recommended_slug: str
    confidence: str
    rationale: str


@dataclass
class WorkflowSemanticEnrichmentInterpretation:
    """Structured AI semantic enrichment output for one evidence segment."""

    actor: str | None
    actor_role: str | None
    system_name: str | None
    action_verb: str | None
    action_type: str | None
    business_object: str | None
    workflow_goal: str | None
    rule_hints: list[str]
    domain_terms: list[str]
    confidence: str
    rationale: str


@dataclass
class ProcessSummaryInterpretation:
    """Structured AI-generated business summary for one process group."""

    summary_text: str
    confidence: str
    rationale: str


@dataclass
class WorkflowCapabilityInterpretation:
    """Structured AI-generated capability tags for one workflow group."""

    capability_tags: list[str]
    confidence: str
    rationale: str


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

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You classify transcript-derived steps into business process groups. "
                        "Return strict JSON with keys: process_title, canonical_slug, matched_existing_title. "
                        "process_title must be a concise business workflow title such as Sales Order Creation. "
                        "canonical_slug must be lowercase kebab-case and stable. "
                        "matched_existing_title must be either one exact title from existing_titles or an empty string. "
                        "Only match an existing title when the process is genuinely the same workflow. "
                        "If the process is different, return an empty matched_existing_title."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "transcript_name": transcript_name,
                            "existing_titles": existing_titles,
                            "steps": [
                                {
                                    "application_name": step.get("application_name", ""),
                                    "action_text": step.get("action_text", ""),
                                    "supporting_transcript_text": step.get("supporting_transcript_text", ""),
                                }
                                for step in steps[:12]
                            ],
                            "notes": [
                                {
                                    "text": note.get("text", ""),
                                    "inference_type": note.get("inference_type", ""),
                                }
                                for note in notes[:6]
                            ],
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

        body = self._post_chat_completion(endpoint=endpoint, headers=headers, payload=payload, context="process-group inference")
        content = self._extract_content(body)
        parsed = self._parse_json_object(content)
        process_title = str(parsed.get("process_title", "") or "").strip()
        canonical_slug = str(parsed.get("canonical_slug", "") or "").strip().lower()
        matched_existing_title = str(parsed.get("matched_existing_title", "") or "").strip() or None
        if not process_title:
            return None
        return ProcessGroupInterpretation(
            process_title=process_title,
            canonical_slug=canonical_slug,
            matched_existing_title=matched_existing_title,
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

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You resolve ambiguous workflow-group assignments for transcript-derived evidence. "
                        "Return strict JSON with keys: matched_existing_title, recommended_title, recommended_slug, confidence, rationale. "
                        "matched_existing_title must be either one exact title from candidate_titles or an empty string if a new workflow should be created. "
                        "recommended_title must be the workflow title that should be used. "
                        "recommended_slug must be lowercase kebab-case. "
                        "confidence must be one of high, medium, low, unknown. "
                        "Prefer matching an existing workflow only if the evidence clearly supports the same business workflow. "
                        "If the evidence is materially different, return an empty matched_existing_title and recommend a new workflow title."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "transcript_name": transcript_name,
                            "inferred_title": inferred_title,
                            "candidate_titles": [item.get("group_title", "") for item in candidate_matches],
                            "candidate_matches": candidate_matches,
                            "steps": [
                                {
                                    "application_name": step.get("application_name", ""),
                                    "action_text": step.get("action_text", ""),
                                    "supporting_transcript_text": step.get("supporting_transcript_text", ""),
                                }
                                for step in steps[:12]
                            ],
                            "notes": [
                                {
                                    "text": note.get("text", ""),
                                    "inference_type": note.get("inference_type", ""),
                                }
                                for note in notes[:6]
                            ],
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
        body = self._post_chat_completion(endpoint=endpoint, headers=headers, payload=payload, context="ambiguous process-group resolution")
        content = self._extract_content(body)
        parsed = self._parse_json_object(content)
        recommended_title = str(parsed.get("recommended_title", "") or "").strip() or inferred_title
        recommended_slug = str(parsed.get("recommended_slug", "") or "").strip().lower()
        matched_existing_title = str(parsed.get("matched_existing_title", "") or "").strip() or None
        rationale = str(parsed.get("rationale", "") or "").strip()
        return AmbiguousProcessGroupResolution(
            matched_existing_title=matched_existing_title,
            recommended_title=recommended_title,
            recommended_slug=recommended_slug,
            confidence=self._normalize_confidence(parsed.get("confidence")),
            rationale=rationale,
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

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You normalize workflow evidence into a concise business workflow title. "
                        "Return strict JSON with keys: workflow_title, canonical_slug, confidence, rationale. "
                        "workflow_title must be a concise business noun phrase such as Sales Order Creation. "
                        "Prefer the stable operational workflow identity over raw UI phrasing. "
                        "Use the business object, workflow goal, system context, and repeated action pattern to infer the title. "
                        "Avoid UI action labels like Open, Go To, Click, Navigate, Select, or Enter as the leading verb. "
                        "Do not use a broad domain label such as Legal Analysis or Procurement unless the evidence does not support a more specific operational workflow title. "
                        "Use tool names only when the tool materially defines a different operational workflow identity. "
                        "canonical_slug must be lowercase kebab-case. "
                        "confidence must be one of high, medium, low, unknown."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "transcript_name": transcript_name,
                            "workflow_summary": workflow_summary,
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
        body = self._post_chat_completion(endpoint=endpoint, headers=headers, payload=payload, context="workflow title resolution")
        content = self._extract_content(body)
        parsed = self._parse_json_object(content)
        workflow_title = self._normalize_label(str(parsed.get("workflow_title", "") or ""))
        if not workflow_title:
            return None
        canonical_slug = self._normalize_slug(
            str(parsed.get("canonical_slug", "") or ""),
            fallback=workflow_title,
        )
        rationale = str(parsed.get("rationale", "") or "").strip()
        confidence = self._normalize_confidence(parsed.get("confidence"))
        confidence = self._calibrate_confidence(
            confidence,
            evidence_points=self._workflow_evidence_points(workflow_summary),
            quality_points=self._title_quality_points(workflow_title),
        )
        return WorkflowTitleInterpretation(
            workflow_title=workflow_title,
            canonical_slug=canonical_slug,
            confidence=confidence,
            rationale=rationale,
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

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You classify whether two adjacent evidence segments belong to the same business workflow. "
                        "Return strict JSON with keys: decision, confidence, rationale. "
                        "decision must be one of same_workflow, new_workflow, uncertain. "
                        "confidence must be one of high, medium, low, unknown. "
                        "Use the workflow goal, business object, actor, system, action type, domain terms, rule hints, and transcript wording. "
                        "Prefer same_workflow only when the business workflow clearly continues. "
                        "Prefer new_workflow when the adjacent segment appears to start a materially different business activity. "
                        "Use uncertain when the evidence conflicts or remains genuinely ambiguous."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "left_segment": left_segment,
                            "right_segment": right_segment,
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
        body = self._post_chat_completion(endpoint=endpoint, headers=headers, payload=payload, context="workflow boundary classification")
        content = self._extract_content(body)
        parsed = self._parse_json_object(content)
        decision = str(parsed.get("decision", "") or "").strip().lower()
        if decision not in {"same_workflow", "new_workflow", "uncertain"}:
            return None
        rationale = str(parsed.get("rationale", "") or "").strip()
        return WorkflowBoundaryInterpretation(
            decision=decision,
            confidence=self._normalize_confidence(parsed.get("confidence")),
            rationale=rationale,
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

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You decide whether new transcript-derived workflow evidence matches an existing workflow group. "
                        "Return strict JSON with keys: matched_existing_title, recommended_title, recommended_slug, confidence, rationale. "
                        "matched_existing_title must be either one exact title from existing_group_titles or an empty string. "
                        "recommended_title must be the workflow title that should be used. "
                        "recommended_slug must be lowercase kebab-case. "
                        "confidence must be one of high, medium, low, unknown. "
                        "Only choose an existing workflow when the operational workflow is materially the same. "
                        "Do not merge workflows only because they belong to the same business domain or professional function. "
                        "Different tools, different application contexts, or materially different interaction sequences should usually remain separate workflows. "
                        "Operational sameness should be evaluated using system context, business object flow, entry point, repeated action pattern, and outcome. "
                        "If only broad domain overlap exists, prefer creating a separate workflow and lower confidence."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "transcript_name": transcript_name,
                            "workflow_summary": workflow_summary,
                            "existing_group_titles": [group.get("title", "") for group in existing_groups],
                            "existing_groups": existing_groups,
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
        body = self._post_chat_completion(endpoint=endpoint, headers=headers, payload=payload, context="workflow group matching")
        content = self._extract_content(body)
        parsed = self._parse_json_object(content)
        recommended_title = self._normalize_label(str(parsed.get("recommended_title", "") or ""))
        if not recommended_title:
            return None
        recommended_slug = self._normalize_slug(
            str(parsed.get("recommended_slug", "") or ""),
            fallback=recommended_title,
        )
        matched_existing_title = self._normalize_existing_title(
            str(parsed.get("matched_existing_title", "") or ""),
            existing_titles=[str(group.get("title", "") or "") for group in existing_groups],
        )
        rationale = str(parsed.get("rationale", "") or "").strip()
        confidence = self._normalize_confidence(parsed.get("confidence"))
        confidence = self._calibrate_confidence(
            confidence,
            evidence_points=self._workflow_evidence_points(workflow_summary),
            quality_points=2 if recommended_title else 0,
            lower_when=min(3, max(len(existing_groups) - 1, 0)),
        )
        return WorkflowGroupMatchInterpretation(
            matched_existing_title=matched_existing_title,
            recommended_title=recommended_title,
            recommended_slug=recommended_slug,
            confidence=confidence,
            rationale=rationale,
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

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You enrich one workflow evidence segment with business workflow labels. "
                        "Return strict JSON with keys: actor, actor_role, system_name, action_verb, action_type, "
                        "business_object, workflow_goal, rule_hints, domain_terms, confidence, rationale. "
                        "actor_role should be a concise role like operator, approver, reviewer, external_party, or system. "
                        "action_type should be a concise business action category such as navigate, create, update, review, approve, validate, extract, or submit. "
                        "workflow_goal should be a concise business goal phrase, not a raw UI action. "
                        "rule_hints and domain_terms must be arrays. "
                        "Prefer operationally meaningful labels over generic domain labels. "
                        "Use null for unknown scalar fields rather than guessing. "
                        "confidence must be one of high, medium, low, unknown. "
                        "Lower confidence when the segment does not contain enough evidence to support a precise operational interpretation."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "transcript_name": transcript_name or "",
                            "segment_context": segment_context or {},
                            "segment_text": segment_text,
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
        body = self._post_chat_completion(endpoint=endpoint, headers=headers, payload=payload, context="workflow semantic enrichment")
        content = self._extract_content(body)
        parsed = self._parse_json_object(content)
        domain_terms = self._normalize_label_list(parsed.get("domain_terms", []), max_items=6)
        rule_hints = self._normalize_label_list(parsed.get("rule_hints", []), max_items=4)
        confidence = self._normalize_confidence(parsed.get("confidence"))
        filled_fields = sum(
            1
            for value in (
                parsed.get("actor"),
                parsed.get("actor_role"),
                parsed.get("system_name"),
                parsed.get("action_verb"),
                parsed.get("action_type"),
                parsed.get("business_object"),
                parsed.get("workflow_goal"),
            )
            if self._normalize_optional_text(value)
        )
        confidence = self._calibrate_confidence(
            confidence,
            evidence_points=filled_fields,
            quality_points=len(domain_terms) + len(rule_hints),
        )
        return WorkflowSemanticEnrichmentInterpretation(
            actor=self._normalize_optional_text(parsed.get("actor")),
            actor_role=self._normalize_optional_text(parsed.get("actor_role")),
            system_name=self._normalize_optional_text(parsed.get("system_name")),
            action_verb=self._normalize_optional_text(parsed.get("action_verb")),
            action_type=self._normalize_optional_text(parsed.get("action_type")),
            business_object=self._normalize_optional_text(parsed.get("business_object")),
            workflow_goal=self._normalize_optional_text(parsed.get("workflow_goal")),
            rule_hints=rule_hints,
            domain_terms=domain_terms,
            confidence=confidence,
            rationale=str(parsed.get("rationale", "") or "").strip(),
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

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate a concise business summary for one resolved workflow group. "
                        "Return strict JSON with keys: summary_text, confidence, rationale. "
                        "summary_text must be 2 to 4 plain-English sentences that describe the workflow purpose, the main business actions, "
                        "and the business outcome. "
                        "Do not produce bullet points. "
                        "Do not zigzag across unrelated workflows. "
                        "Keep the summary scoped only to the provided workflow evidence. "
                        "Use business language instead of UI click-by-click language when possible. "
                        "Prefer the operational workflow identity and business outcome over raw transcript wording. "
                        "confidence must be one of high, medium, low, unknown."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "document_type": document_type,
                            "process_title": process_title,
                            "workflow_summary": workflow_summary,
                            "steps": [
                                {
                                    "application_name": step.get("application_name", ""),
                                    "action_text": step.get("action_text", ""),
                                    "supporting_transcript_text": step.get("supporting_transcript_text", ""),
                                }
                                for step in steps[:12]
                            ],
                            "notes": [
                                {
                                    "text": note.get("text", ""),
                                    "inference_type": note.get("inference_type", ""),
                                }
                                for note in notes[:6]
                            ],
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
        body = self._post_chat_completion(endpoint=endpoint, headers=headers, payload=payload, context="process summary generation")
        content = self._extract_content(body)
        parsed = self._parse_json_object(content)
        summary_text = str(parsed.get("summary_text", "") or "").strip()
        if not summary_text:
            return None
        confidence = self._normalize_confidence(parsed.get("confidence"))
        confidence = self._calibrate_confidence(
            confidence,
            evidence_points=self._workflow_evidence_points(workflow_summary),
            quality_points=self._summary_quality_points(summary_text),
        )
        return ProcessSummaryInterpretation(
            summary_text=summary_text,
            confidence=confidence,
            rationale=str(parsed.get("rationale", "") or "").strip(),
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

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You classify broader business capability tags for one workflow. "
                        "Return strict JSON with keys: capability_tags, confidence, rationale. "
                        "capability_tags must be a short list of 1 to 3 business capability labels such as Contract Review, Legal Document Analysis, Sales Operations, or Procurement. "
                        "These tags describe broad business capability and must not redefine workflow identity. "
                        "Do not return tool names, exact workflow titles, or low-value generic labels. "
                        "Prefer reusable cross-tool business capability labels. "
                        "confidence must be one of high, medium, low, unknown."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "document_type": document_type,
                            "process_title": process_title,
                            "workflow_summary": workflow_summary,
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
        body = self._post_chat_completion(endpoint=endpoint, headers=headers, payload=payload, context="workflow capability classification")
        content = self._extract_content(body)
        parsed = self._parse_json_object(content)
        capability_tags = self._normalize_label_list(
            parsed.get("capability_tags", []),
            max_items=3,
            exclude={process_title},
        )
        confidence = self._normalize_confidence(parsed.get("confidence"))
        confidence = self._calibrate_confidence(
            confidence,
            evidence_points=self._workflow_evidence_points(workflow_summary),
            quality_points=len(capability_tags),
        )
        return WorkflowCapabilityInterpretation(
            capability_tags=capability_tags,
            confidence=confidence,
            rationale=str(parsed.get("rationale", "") or "").strip(),
        )

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
        if httpx is None:
            raise RuntimeError("AI HTTP client dependency 'httpx' is not installed.")
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
    def _normalize_step(item: Mapping[str, Any], transcript_artifact_id: str) -> StepRecord:
        """Normalize one AI-produced step into the worker's step shape."""
        start_timestamp = AITranscriptInterpreter._normalize_timestamp(str(item.get("start_timestamp", "") or ""))
        end_timestamp = AITranscriptInterpreter._normalize_timestamp(str(item.get("end_timestamp", "") or ""))
        display_timestamp = AITranscriptInterpreter._normalize_timestamp(
            str(item.get("display_timestamp", item.get("timestamp", "")) or "")
        )
        supporting_transcript_text = str(item.get("supporting_transcript_text", "") or "").strip()
        locator = display_timestamp or start_timestamp or "ai:transcript"
        return {
            "id": str(uuid4()),
            "process_group_id": None,
            "meeting_id": None,
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
    def _normalize_note(item: Mapping[str, Any]) -> NoteRecord:
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

    @classmethod
    def _calibrate_confidence(
        cls,
        confidence: str,
        *,
        evidence_points: int,
        quality_points: int,
        lower_when: int = 2,
    ) -> str:
        rank = cls._confidence_rank(confidence)
        if evidence_points <= lower_when:
            rank = min(rank, 1)
        elif evidence_points <= lower_when + 1 and rank > 1:
            rank -= 1
        if quality_points <= 0:
            rank = min(rank, 1)
        elif quality_points == 1 and rank > 1:
            rank -= 1
        return cls._confidence_from_rank(rank)

    @staticmethod
    def _confidence_rank(confidence: str) -> int:
        return {"unknown": 0, "low": 1, "medium": 2, "high": 3}.get(confidence, 1)

    @staticmethod
    def _confidence_from_rank(rank: int) -> str:
        return {0: "unknown", 1: "low", 2: "medium", 3: "high"}.get(max(0, min(rank, 3)), "low")

    @staticmethod
    def _workflow_evidence_points(workflow_summary: dict[str, Any]) -> int:
        score = 0
        for key in ("top_actors", "top_objects", "top_systems", "top_actions", "top_goals", "top_rules", "top_domain_terms"):
            values = workflow_summary.get(key, [])
            if isinstance(values, list) and any(str(value).strip() for value in values):
                score += 1
        for key in ("step_samples", "note_samples"):
            values = workflow_summary.get(key, [])
            if isinstance(values, list) and any(values):
                score += 1
        return score

    @staticmethod
    def _title_quality_points(workflow_title: str) -> int:
        token_count = len([token for token in re.split(r"\s+", workflow_title.strip()) if token])
        if token_count < 2:
            return 0
        if token_count <= 6:
            return 2
        return 1

    @staticmethod
    def _summary_quality_points(summary_text: str) -> int:
        sentence_count = len([part for part in re.split(r"[.!?]+", summary_text) if part.strip()])
        if sentence_count < 2:
            return 0
        if sentence_count <= 4:
            return 2
        return 1

    @staticmethod
    def _normalize_slug(value: str, *, fallback: str) -> str:
        normalized_source = value.strip() or fallback
        normalized = re.sub(r"[^a-z0-9\s-]+", " ", normalized_source.lower())
        collapsed = re.sub(r"\s+", "-", normalized.strip())
        return re.sub(r"-{2,}", "-", collapsed).strip("-") or "process"

    @staticmethod
    def _normalize_existing_title(value: str, *, existing_titles: list[str]) -> str | None:
        candidate = value.strip()
        if not candidate:
            return None
        return candidate if candidate in existing_titles else None

    @staticmethod
    def _normalize_label(value: str) -> str:
        normalized = re.sub(r"\s+", " ", value.strip())
        return normalized[:120].strip()

    @classmethod
    def _normalize_label_list(
        cls,
        values: Any,
        *,
        max_items: int,
        exclude: set[str] | None = None,
    ) -> list[str]:
        if not isinstance(values, list):
            return []
        excluded = {cls._normalize_textish(item) for item in (exclude or set()) if cls._normalize_textish(item)}
        normalized_items: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                continue
            cleaned = cls._normalize_label(value)
            if not cleaned:
                continue
            normalized_key = cls._normalize_textish(cleaned)
            if not normalized_key or normalized_key in seen or normalized_key in excluded:
                continue
            seen.add(normalized_key)
            normalized_items.append(cleaned)
            if len(normalized_items) >= max_items:
                break
        return normalized_items

    @staticmethod
    def _normalize_textish(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
        return re.sub(r"\s+", " ", normalized).strip()

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

    @staticmethod
    def _normalize_optional_text(value: Any) -> str | None:
        """Normalize optional scalar text fields from AI output."""
        normalized = str(value or "").strip()
        return normalized or None
