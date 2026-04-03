from __future__ import annotations

import json
from collections import defaultdict
from typing import cast

from app.core.observability import get_logger
from app.models.process_group import ProcessGroupModel
from worker.services.ai_skills.process_summary_generation.schemas import ProcessSummaryGenerationRequest
from worker.services.generation_types import NoteRecord, StepRecord
from worker.services.workflow_intelligence.grouping_models import TranscriptWorkflowProfile
from worker.services.workflow_intelligence.grouping_title_resolution import operation_signature_from_steps

logger = get_logger(__name__)


def merge_profile_lists(
    workflow_profiles: list[TranscriptWorkflowProfile],
    attribute_name: str,
    *,
    limit: int,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for profile in workflow_profiles:
        for value in getattr(profile, attribute_name):
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
            if len(ordered) >= limit:
                return ordered
    return ordered


def build_group_workflow_summary(
    *,
    title: str,
    workflow_profiles: list[TranscriptWorkflowProfile],
    steps: list[StepRecord],
    notes: list[NoteRecord],
) -> dict[str, object]:
    return {
        "suggested_title": title,
        "top_actors": merge_profile_lists(workflow_profiles, "top_actors", limit=4),
        "top_objects": merge_profile_lists(workflow_profiles, "top_objects", limit=4),
        "top_systems": merge_profile_lists(workflow_profiles, "top_systems", limit=4),
        "top_applications": merge_profile_lists(workflow_profiles, "top_applications", limit=4),
        "top_actions": merge_profile_lists(workflow_profiles, "top_actions", limit=4),
        "top_goals": merge_profile_lists(workflow_profiles, "top_goals", limit=4),
        "top_rules": merge_profile_lists(workflow_profiles, "top_rules", limit=4),
        "top_domain_terms": merge_profile_lists(workflow_profiles, "top_domain_terms", limit=6),
        "operational_signature": operation_signature_from_steps(steps),
        "step_samples": [
            {
                "action_text": str(step.get("action_text", "") or ""),
                "supporting_transcript_text": str(step.get("supporting_transcript_text", "") or ""),
            }
            for step in steps[:10]
        ],
        "note_samples": [str(note.get("text", "") or "") for note in notes[:6]],
    }


def build_process_summary_fallback(
    *,
    process_title: str,
    workflow_profiles: list[TranscriptWorkflowProfile],
    steps: list[StepRecord],
    notes: list[NoteRecord],
) -> str:
    top_goals = merge_profile_lists(workflow_profiles, "top_goals", limit=2)
    top_objects = merge_profile_lists(workflow_profiles, "top_objects", limit=3)
    top_systems = merge_profile_lists(workflow_profiles, "top_systems", limit=2)
    top_rules = merge_profile_lists(workflow_profiles, "top_rules", limit=2)
    summary_parts = [f"{process_title} covers the workflow"]
    if top_goals:
        summary_parts.append(f"focused on {', '.join(top_goals)}")
    elif top_objects:
        summary_parts.append(f"focused on {', '.join(top_objects)}")
    if top_systems:
        summary_parts.append(f"using {', '.join(top_systems)}")
    sentence_one = " ".join(summary_parts).strip().rstrip(".") + "."

    key_actions = [
        str(step.get("action_text", "") or "").strip()
        for step in steps[:3]
        if str(step.get("action_text", "") or "").strip()
    ]
    sentence_two = f"Key business actions include {', '.join(key_actions)}." if key_actions else ""

    sentence_three = ""
    if top_rules:
        sentence_three = f"Important workflow considerations include {', '.join(top_rules)}."
    elif notes:
        note_text = str(notes[0].get("text", "") or "").strip()
        if note_text:
            sentence_three = f"Supporting process context includes {note_text}."

    return " ".join(part for part in (sentence_one, sentence_two, sentence_three) if part).strip()


def refresh_group_summaries(
    *,
    process_groups: list[ProcessGroupModel],
    transcript_group_ids: dict[str, str],
    steps_by_transcript: dict[str, list[StepRecord]],
    notes_by_transcript: dict[str, list[NoteRecord]],
    workflow_profiles: dict[str, TranscriptWorkflowProfile],
    document_type: str,
    ai_skill,
    accepted_ai_confidence: set[str],
    resolve_capability_tags,
) -> None:
    if not process_groups:
        return

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
        logger.info(
            "Delegating process summary generation to AI skill.",
            extra={
                "skill_id": "process_summary_generation",
                "skill_version": getattr(ai_skill, "version", "unknown"),
                "process_title": process_group.title,
            },
        )
        ai_summary = ai_skill.run(
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
        process_group.capability_tags_json = json.dumps(
            resolve_capability_tags(
                process_title=process_group.title,
                workflow_summary=workflow_summary,
                workflow_profiles=group_profiles,
                document_type=document_type,
            )
        )

