from __future__ import annotations

from worker.pipeline.types import NoteRecord, StepRecord
from worker.grouping.grouping_models import TranscriptWorkflowProfile
from worker.grouping.grouping_profile_lists import merge_profile_lists
from worker.grouping.grouping_profiles import STOPWORDS, normalize_text
from worker.grouping.grouping_text import operation_signature_from_steps, signature_tokens




def group_summary_seed(
    *,
    inferred_title: str,
    steps: list[StepRecord],
    notes: list[NoteRecord],
    workflow_profile: TranscriptWorkflowProfile,
) -> str:
    parts = [inferred_title]
    parts.extend(workflow_profile.top_actors[:2])
    parts.extend(workflow_profile.top_goals[:2])
    parts.extend(workflow_profile.top_objects[:2])
    parts.extend(workflow_profile.top_systems[:2])
    parts.extend(workflow_profile.top_rules[:2])
    parts.extend(str(step.get("action_text", "") or "") for step in steps[:6])
    parts.extend(str(note.get("text", "") or "") for note in notes[:3])
    return " ".join(part for part in parts if part).strip()


def build_workflow_summary(
    *,
    title: str,
    workflow_profile: TranscriptWorkflowProfile,
    steps: list[StepRecord],
    notes: list[NoteRecord],
) -> dict[str, object]:
    return {
        "suggested_title": title,
        "top_actors": workflow_profile.top_actors,
        "top_objects": workflow_profile.top_objects,
        "top_systems": workflow_profile.top_systems,
        "top_applications": workflow_profile.top_applications,
        "top_actions": workflow_profile.top_actions,
        "top_goals": workflow_profile.top_goals,
        "top_rules": workflow_profile.top_rules,
        "top_domain_terms": workflow_profile.top_domain_terms,
        "operational_signature": operation_signature_from_steps(steps),
        "step_samples": [
            {
                "action_text": str(step.get("action_text", "") or ""),
                "supporting_transcript_text": str(step.get("supporting_transcript_text", "") or ""),
            }
            for step in steps[:8]
        ],
        "note_samples": [str(note.get("text", "") or "") for note in notes[:4]],
    }


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
    key_actions = [str(step.get("action_text", "") or "").strip() for step in steps[:3] if str(step.get("action_text", "") or "").strip()]
    sentence_two = f"Key business actions include {', '.join(key_actions)}." if key_actions else ""
    sentence_three = ""
    if top_rules:
        sentence_three = f"Important workflow considerations include {', '.join(top_rules)}."
    elif notes:
        note_text = str(notes[0].get("text", "") or "").strip()
        if note_text:
            sentence_three = f"Supporting process context includes {note_text}."
    return " ".join(part for part in (sentence_one, sentence_two, sentence_three) if part).strip()
