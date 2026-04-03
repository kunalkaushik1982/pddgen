from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from worker.services.ai_transcript.client import extract_content, parse_json_object, post_chat_completion
from worker.services.ai_transcript.models import (
    AmbiguousProcessGroupResolution,
    ProcessGroupInterpretation,
    ProcessSummaryInterpretation,
    WorkflowBoundaryInterpretation,
    WorkflowCapabilityInterpretation,
    WorkflowGroupMatchInterpretation,
    WorkflowSemanticEnrichmentInterpretation,
    WorkflowTitleInterpretation,
)
from worker.services.ai_transcript.normalization import (
    calibrate_confidence,
    normalize_confidence,
    normalize_existing_title,
    normalize_label,
    normalize_label_list,
    normalize_optional_text,
    normalize_slug,
    summary_quality_points,
    title_quality_points,
    workflow_evidence_points,
)


def _post_json(*, settings: Any, payload: dict[str, Any], context: str) -> dict[str, Any]:
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


def infer_process_group(
    *,
    settings: Any,
    transcript_name: str,
    steps: Sequence[Mapping[str, Any]],
    notes: Sequence[Mapping[str, Any]],
    existing_titles: list[str],
) -> ProcessGroupInterpretation | None:
    payload = {
        "model": settings.ai_model,
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
    parsed = parse_json_object(extract_content(_post_json(settings=settings, payload=payload, context="process-group inference")))
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
    *,
    settings: Any,
    transcript_name: str,
    inferred_title: str,
    candidate_matches: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
    notes: Sequence[Mapping[str, Any]],
) -> AmbiguousProcessGroupResolution | None:
    payload = {
        "model": settings.ai_model,
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
    parsed = parse_json_object(
        extract_content(_post_json(settings=settings, payload=payload, context="ambiguous process-group resolution"))
    )
    recommended_title = str(parsed.get("recommended_title", "") or "").strip() or inferred_title
    recommended_slug = str(parsed.get("recommended_slug", "") or "").strip().lower()
    matched_existing_title = str(parsed.get("matched_existing_title", "") or "").strip() or None
    rationale = str(parsed.get("rationale", "") or "").strip()
    return AmbiguousProcessGroupResolution(
        matched_existing_title=matched_existing_title,
        recommended_title=recommended_title,
        recommended_slug=recommended_slug,
        confidence=normalize_confidence(parsed.get("confidence")),
        rationale=rationale,
    )


def resolve_workflow_title(*, settings: Any, transcript_name: str, workflow_summary: dict[str, Any]) -> WorkflowTitleInterpretation | None:
    payload = {
        "model": settings.ai_model,
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
            {"role": "user", "content": json.dumps({"transcript_name": transcript_name, "workflow_summary": workflow_summary}, ensure_ascii=False)},
        ],
    }
    parsed = parse_json_object(extract_content(_post_json(settings=settings, payload=payload, context="workflow title resolution")))
    workflow_title = normalize_label(str(parsed.get("workflow_title", "") or ""))
    if not workflow_title:
        return None
    confidence = calibrate_confidence(
        normalize_confidence(parsed.get("confidence")),
        evidence_points=workflow_evidence_points(workflow_summary),
        quality_points=title_quality_points(workflow_title),
    )
    return WorkflowTitleInterpretation(
        workflow_title=workflow_title,
        canonical_slug=normalize_slug(str(parsed.get("canonical_slug", "") or ""), fallback=workflow_title),
        confidence=confidence,
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )


def classify_workflow_boundary(
    *,
    settings: Any,
    left_segment: dict[str, Any],
    right_segment: dict[str, Any],
) -> WorkflowBoundaryInterpretation | None:
    payload = {
        "model": settings.ai_model,
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
            {"role": "user", "content": json.dumps({"left_segment": left_segment, "right_segment": right_segment}, ensure_ascii=False)},
        ],
    }
    parsed = parse_json_object(
        extract_content(_post_json(settings=settings, payload=payload, context="workflow boundary classification"))
    )
    decision = str(parsed.get("decision", "") or "").strip().lower()
    if decision not in {"same_workflow", "new_workflow", "uncertain"}:
        return None
    return WorkflowBoundaryInterpretation(
        decision=decision,
        confidence=normalize_confidence(parsed.get("confidence")),
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )


def match_existing_workflow_group(
    *,
    settings: Any,
    transcript_name: str,
    workflow_summary: dict[str, Any],
    existing_groups: list[dict[str, Any]],
) -> WorkflowGroupMatchInterpretation | None:
    payload = {
        "model": settings.ai_model,
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
    parsed = parse_json_object(extract_content(_post_json(settings=settings, payload=payload, context="workflow group matching")))
    recommended_title = normalize_label(str(parsed.get("recommended_title", "") or ""))
    if not recommended_title:
        return None
    confidence = calibrate_confidence(
        normalize_confidence(parsed.get("confidence")),
        evidence_points=workflow_evidence_points(workflow_summary),
        quality_points=2 if recommended_title else 0,
        lower_when=min(3, max(len(existing_groups) - 1, 0)),
    )
    return WorkflowGroupMatchInterpretation(
        matched_existing_title=normalize_existing_title(
            str(parsed.get("matched_existing_title", "") or ""),
            existing_titles=[str(group.get("title", "") or "") for group in existing_groups],
        ),
        recommended_title=recommended_title,
        recommended_slug=normalize_slug(str(parsed.get("recommended_slug", "") or ""), fallback=recommended_title),
        confidence=confidence,
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )


def enrich_workflow_segment(
    *,
    settings: Any,
    segment_text: str,
    transcript_name: str | None = None,
    segment_context: dict[str, Any] | None = None,
) -> WorkflowSemanticEnrichmentInterpretation | None:
    payload = {
        "model": settings.ai_model,
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
    parsed = _post_and_extract(settings=settings, payload=payload, context="workflow semantic enrichment")
    domain_terms = normalize_label_list(parsed.get("domain_terms", []), max_items=6)
    rule_hints = normalize_label_list(parsed.get("rule_hints", []), max_items=4)
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
        if normalize_optional_text(value)
    )
    confidence = calibrate_confidence(
        normalize_confidence(parsed.get("confidence")),
        evidence_points=filled_fields,
        quality_points=len(domain_terms) + len(rule_hints),
    )
    return WorkflowSemanticEnrichmentInterpretation(
        actor=normalize_optional_text(parsed.get("actor")),
        actor_role=normalize_optional_text(parsed.get("actor_role")),
        system_name=normalize_optional_text(parsed.get("system_name")),
        action_verb=normalize_optional_text(parsed.get("action_verb")),
        action_type=normalize_optional_text(parsed.get("action_type")),
        business_object=normalize_optional_text(parsed.get("business_object")),
        workflow_goal=normalize_optional_text(parsed.get("workflow_goal")),
        rule_hints=rule_hints,
        domain_terms=domain_terms,
        confidence=confidence,
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )


def summarize_process_group(
    *,
    settings: Any,
    process_title: str,
    workflow_summary: dict[str, Any],
    steps: Sequence[Mapping[str, Any]],
    notes: Sequence[Mapping[str, Any]],
    document_type: str,
) -> ProcessSummaryInterpretation | None:
    payload = {
        "model": settings.ai_model,
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
    parsed = parse_json_object(extract_content(_post_json(settings=settings, payload=payload, context="process summary generation")))
    summary_text = str(parsed.get("summary_text", "") or "").strip()
    if not summary_text:
        return None
    confidence = calibrate_confidence(
        normalize_confidence(parsed.get("confidence")),
        evidence_points=workflow_evidence_points(workflow_summary),
        quality_points=summary_quality_points(summary_text),
    )
    return ProcessSummaryInterpretation(
        summary_text=summary_text,
        confidence=confidence,
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )


def classify_workflow_capabilities(
    *,
    settings: Any,
    process_title: str,
    workflow_summary: dict[str, Any],
    document_type: str,
) -> WorkflowCapabilityInterpretation | None:
    payload = {
        "model": settings.ai_model,
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
                    {"document_type": document_type, "process_title": process_title, "workflow_summary": workflow_summary},
                    ensure_ascii=False,
                ),
            },
        ],
    }
    parsed = parse_json_object(
        extract_content(_post_json(settings=settings, payload=payload, context="workflow capability classification"))
    )
    capability_tags = normalize_label_list(parsed.get("capability_tags", []), max_items=3, exclude={process_title})
    confidence = calibrate_confidence(
        normalize_confidence(parsed.get("confidence")),
        evidence_points=workflow_evidence_points(workflow_summary),
        quality_points=len(capability_tags),
    )
    return WorkflowCapabilityInterpretation(
        capability_tags=capability_tags,
        confidence=confidence,
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )


def _post_and_extract(*, settings: Any, payload: dict[str, Any], context: str) -> dict[str, Any]:
    return parse_json_object(extract_content(_post_json(settings=settings, payload=payload, context=context)))
