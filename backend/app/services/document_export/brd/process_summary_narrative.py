r"""
BRD-oriented process summary paragraphs (business-facing wording without PDD/AS-IS jargon).
"""

from __future__ import annotations

from typing import Any

from app.models.draft_session import DraftSessionModel


def build_brd_section_summary(
    *,
    process_name: str,
    process_steps: list[dict[str, Any]],
    process_notes: list[dict[str, Any]],
) -> str:
    applications = [
        item
        for item in dict.fromkeys(
            str(step.get("application_name", "") or "").strip()
            for step in process_steps
        )
        if item
    ]
    action_samples = [
        str(step.get("action_text", "") or "").strip().rstrip(".")
        for step in process_steps[:4]
        if str(step.get("action_text", "") or "").strip()
    ]
    note_samples = [
        str(note.get("text", "") or "").strip().rstrip(".")
        for note in process_notes[:2]
        if str(note.get("text", "") or "").strip()
    ]

    name = (process_name or "the business process under review").strip()
    application_text = ", ".join(applications) if applications else "the relevant business systems"
    step_count = len(process_steps)

    summary_parts = [
        (
            f"This summary describes the business context for {name}. It is based on a structured review "
            f"of how the process is performed using {application_text}. The evidence comprises "
            f"{step_count} ordered activit{'ies' if step_count != 1 else 'y'} that inform scope, stakeholders, and requirements."
        )
    ]

    if action_samples:
        if len(action_samples) == 1:
            action_text = action_samples[0]
        else:
            action_text = ", ".join(action_samples[:-1]) + f", and {action_samples[-1]}"
        summary_parts.append(
            f"Representative activities include {action_text}, illustrating how work progresses from initiation through validation and completion."
        )

    if applications:
        summary_parts.append(
            f"Systems and applications involved include {application_text}, which together provide the entry points, controls, and checkpoints needed to complete the work."
        )

    if note_samples:
        note_text = note_samples[0] if len(note_samples) == 1 else " and ".join(note_samples)
        summary_parts.append(
            f"Additional business context recorded during the review includes {note_text}, clarifying intent, dependencies, and control expectations."
        )

    summary_parts.append(
        "Use this summary together with the requirements, workflow, and diagram sections that follow to align on business needs and constraints."
    )
    return " ".join(summary_parts)


def build_brd_process_summary(
    draft_session: DraftSessionModel,
    process_steps: list[dict[str, Any]],
    process_notes: list[dict[str, Any]],
) -> str:
    process_groups = sorted(getattr(draft_session, "process_groups", []), key=lambda item: item.display_order)
    if len(process_groups) > 1:
        grouped_sections: list[str] = []
        for process_group in process_groups:
            group_steps = [step for step in process_steps if step.get("process_group_id") == process_group.id]
            group_notes = [note for note in process_notes if note.get("process_group_id") == process_group.id]
            if not group_steps and not group_notes:
                continue
            grouped_sections.append(
                build_brd_section_summary(
                    process_name=process_group.title or draft_session.title,
                    process_steps=group_steps,
                    process_notes=group_notes,
                )
            )
        if grouped_sections:
            return " ".join(grouped_sections)

    return build_brd_section_summary(
        process_name=draft_session.title,
        process_steps=process_steps,
        process_notes=process_notes,
    )
