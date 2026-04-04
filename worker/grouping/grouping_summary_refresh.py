from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, cast

from app.models.process_group import ProcessGroupModel
from worker.ai_skills.process_summary_generation.schemas import ProcessSummaryGenerationRequest
from worker.ai_skills.workflow_capability_tagging.schemas import WorkflowCapabilityTaggingRequest
from worker.pipeline.types import NoteRecord, StepRecord
from worker.grouping.grouping_models import (
    CandidateMatchRecord,
    HeuristicGroupMatchResult,
    TranscriptWorkflowProfile,
)
from worker.grouping.grouping_profiles import merge_profile_lists, normalize_text, STOPWORDS
from worker.grouping.grouping_summaries import (
    build_group_workflow_summary,
    build_process_summary_fallback,
    normalize_capability_tags,
    parse_capability_tags,
    to_capability_label,
)


def refresh_group_summaries(
    *,
    process_groups: list[ProcessGroupModel],
    transcript_group_ids: dict[str, str],
    steps_by_transcript: dict[str, list[StepRecord]],
    notes_by_transcript: dict[str, list[NoteRecord]],
    workflow_profiles: dict[str, TranscriptWorkflowProfile],
    document_type: str,
    accepted_ai_confidence: set[str],
    ai_skill_registry: Any,
    process_summary_generation_skill: Any,
    workflow_capability_tagging_skill: Any,
    logger: Any,
) -> tuple[Any, Any]:
    if not process_groups:
        return process_summary_generation_skill, workflow_capability_tagging_skill

    transcript_ids_by_group: dict[str, list[str]] = defaultdict(list)
    for transcript_id, group_id in transcript_group_ids.items():
        transcript_ids_by_group[group_id].append(transcript_id)

    for process_group in process_groups:
        transcript_ids = transcript_ids_by_group.get(process_group.id, [])
        group_steps = [
            cast(StepRecord, dict(step))
            for transcript_id in transcript_ids
            for step in steps_by_transcript.get(transcript_id, [])
        ]
        group_notes = [
            cast(NoteRecord, dict(note))
            for transcript_id in transcript_ids
            for note in notes_by_transcript.get(transcript_id, [])
        ]
        group_profiles = [
            workflow_profiles[transcript_id]
            for transcript_id in transcript_ids
            if transcript_id in workflow_profiles
        ]
        fallback_summary = build_process_summary_fallback(
            process_title=process_group.title,
            workflow_profiles=group_profiles,
            steps=group_steps,
            notes=group_notes,
        )
        workflow_summary = build_group_workflow_summary(
            title=process_group.title,
            workflow_profiles=group_profiles,
            steps=group_steps,
            notes=group_notes,
        )
        if process_summary_generation_skill is None:
            process_summary_generation_skill = ai_skill_registry.create("process_summary_generation")
        logger.info(
            "Delegating process summary generation to AI skill.",
            extra={
                "skill_id": "process_summary_generation",
                "skill_version": getattr(process_summary_generation_skill, "version", "unknown"),
                "process_title": process_group.title,
            },
        )
        ai_summary = process_summary_generation_skill.run(
            ProcessSummaryGenerationRequest(
                process_title=process_group.title,
                workflow_summary=workflow_summary,
                steps=group_steps[:12],
                notes=group_notes[:6],
                document_type=document_type,
            )
        )
        if ai_summary is not None and ai_summary.confidence in accepted_ai_confidence:
            process_group.summary_text = ai_summary.summary_text
        else:
            process_group.summary_text = fallback_summary
        capability_tags, workflow_capability_tagging_skill = resolve_capability_tags(
            process_title=process_group.title,
            workflow_summary=workflow_summary,
            workflow_profiles=group_profiles,
            document_type=document_type,
            accepted_ai_confidence=accepted_ai_confidence,
            ai_skill_registry=ai_skill_registry,
            workflow_capability_tagging_skill=workflow_capability_tagging_skill,
            logger=logger,
        )
        process_group.capability_tags_json = json.dumps(capability_tags)

    return process_summary_generation_skill, workflow_capability_tagging_skill


def resolve_capability_tags(
    *,
    process_title: str,
    workflow_summary: dict[str, object],
    workflow_profiles: list[TranscriptWorkflowProfile],
    document_type: str,
    accepted_ai_confidence: set[str],
    ai_skill_registry: Any,
    workflow_capability_tagging_skill: Any,
    logger: Any,
) -> tuple[list[str], Any]:
    if workflow_capability_tagging_skill is None:
        workflow_capability_tagging_skill = ai_skill_registry.create("workflow_capability_tagging")
    logger.info(
        "Delegating workflow capability tagging to AI skill.",
        extra={
            "skill_id": "workflow_capability_tagging",
            "skill_version": getattr(workflow_capability_tagging_skill, "version", "unknown"),
            "process_title": process_title,
        },
    )
    ai_capabilities = workflow_capability_tagging_skill.run(
        WorkflowCapabilityTaggingRequest(
            process_title=process_title,
            workflow_summary=workflow_summary,
            document_type=document_type,
        )
    )
    if (
        ai_capabilities is not None
        and ai_capabilities.confidence in accepted_ai_confidence
        and ai_capabilities.capability_tags
    ):
        normalized_tags = normalize_capability_tags(
            ai_capabilities.capability_tags,
            process_title=process_title,
        )
        if normalized_tags:
            return normalized_tags, workflow_capability_tagging_skill

    fallback_tags = fallback_capability_tags(workflow_profiles=workflow_profiles)
    return (fallback_tags if fallback_tags else [process_title]), workflow_capability_tagging_skill


def fallback_capability_tags(*, workflow_profiles: list[TranscriptWorkflowProfile]) -> list[str]:
    ordered = merge_profile_lists(workflow_profiles, "top_domain_terms", limit=3)
    fallback = [to_capability_label(value) for value in ordered if value]
    return normalize_capability_tags(fallback, process_title="")


def serialize_existing_groups_for_ai(
    *,
    existing_groups: list[ProcessGroupModel],
    heuristic_match: HeuristicGroupMatchResult,
) -> list[dict[str, object]]:
    candidate_scores: dict[str, CandidateMatchRecord] = {
        str(item.get("group_title", "")): item
        for item in heuristic_match["candidate_matches"]
    }
    serialized: list[dict[str, object]] = []
    for group in existing_groups:
        candidate_score = candidate_scores.get(group.title)
        serialized.append(
            {
                "title": group.title,
                "canonical_slug": group.canonical_slug,
                "summary_text": getattr(group, "summary_text", "") or "",
                "capability_tags": parse_capability_tags(getattr(group, "capability_tags_json", "[]")),
                "summary_tokens": [
                    token
                    for token in normalize_text(getattr(group, "summary_text", "") or "").split()
                    if token and token not in STOPWORDS
                ][:10],
                "heuristic_score": candidate_score.get("score") if candidate_score is not None else None,
                "heuristic_title_ratio": candidate_score.get("title_ratio") if candidate_score is not None else None,
                "heuristic_signature_overlap": candidate_score.get("signature_overlap") if candidate_score is not None else None,
                "heuristic_system_alignment": candidate_score.get("system_alignment") if candidate_score is not None else None,
                "heuristic_application_alignment": candidate_score.get("application_alignment") if candidate_score is not None else None,
            }
        )
    return serialized
