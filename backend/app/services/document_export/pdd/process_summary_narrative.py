r"""
PDD-oriented process summary paragraphs (AS-IS wording) for exports that use walkthrough evidence.
"""

from __future__ import annotations

from typing import Any

from app.models.draft_session import DraftSessionModel


def build_pdd_section_summary(
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

    name = (process_name or "the observed business process").strip()
    application_text = ", ".join(applications) if applications else "the supporting business application landscape"
    step_count = len(process_steps)

    summary_parts = [
        (
            f"The AS-IS process documented in this draft captures how {name} is currently executed within "
            f"{application_text}. The walkthrough reflects the observed user activity required to complete the business objective, "
            f"with the process broken into {step_count} ordered step{'s' if step_count != 1 else ''} for review and refinement."
        )
    ]

    if action_samples:
        if len(action_samples) == 1:
            action_text = action_samples[0]
        else:
            action_text = ", ".join(action_samples[:-1]) + f", and {action_samples[-1]}"
        summary_parts.append(
            f"Across the captured flow, the user moves through actions such as {action_text}, showing how the transaction progresses from initiation through validation and completion."
        )

    if applications:
        summary_parts.append(
            f"The applications involved in this process include {application_text}, which together support the operational controls, data entry points, and review checkpoints required to complete the work accurately."
        )

    if note_samples:
        note_text = note_samples[0] if len(note_samples) == 1 else " and ".join(note_samples)
        summary_parts.append(
            f"During the walkthrough, additional business context was also identified, including {note_text}, which helps explain the intent, dependencies, and control expectations behind the recorded steps."
        )

    summary_parts.append(
        "This section should be used as a narrative summary of the current-state process before reviewing the detailed step bullets, primary screenshots, and supporting process flow diagram."
    )
    return " ".join(summary_parts)


def build_pdd_process_summary(
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
                build_pdd_section_summary(
                    process_name=process_group.title or draft_session.title,
                    process_steps=group_steps,
                    process_notes=group_notes,
                )
            )
        if grouped_sections:
            return " ".join(grouped_sections)

    return build_pdd_section_summary(
        process_name=draft_session.title,
        process_steps=process_steps,
        process_notes=process_notes,
    )
