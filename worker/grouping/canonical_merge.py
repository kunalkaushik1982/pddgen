r"""
Purpose: Deterministic canonical merge for multi-meeting draft generation.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\canonical_process_merge.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from app.models.artifact import ArtifactModel
from app.models.process_group import ProcessGroupModel
from worker.pipeline.types import NoteRecord, StepRecord
from worker.grouping.canonical_merge_grouping import (
    group_transcripts_by_process_group,
    note_transcript_id,
    step_transcript_id,
)
from worker.grouping.canonical_merge_matching import merge_notes, merge_steps


@dataclass(slots=True)
class CanonicalMergeResult:
    """Return the canonicalized process state after merging meeting evidence."""

    steps: list[StepRecord]
    notes: list[NoteRecord]
    steps_by_transcript: dict[str, list[StepRecord]]
    notes_by_transcript: dict[str, list[NoteRecord]]


class CanonicalProcessMergeService:
    """Build one current process view from multiple meeting-specific transcript outputs."""

    def merge(
        self,
        *,
        transcript_artifacts: list[ArtifactModel],
        process_groups: list[ProcessGroupModel],
        steps_by_transcript: dict[str, list[StepRecord]],
        notes_by_transcript: dict[str, list[NoteRecord]],
    ) -> CanonicalMergeResult:
        """Apply a latest-wins merge within each process group and append groups in display order."""
        canonical_steps: list[StepRecord] = []
        canonical_notes: list[NoteRecord] = []
        merged_steps_by_transcript: dict[str, list[StepRecord]] = {}
        merged_notes_by_transcript: dict[str, list[NoteRecord]] = {}

        transcripts_by_group = group_transcripts_by_process_group(
            transcript_artifacts=transcript_artifacts,
            steps_by_transcript=steps_by_transcript,
            notes_by_transcript=notes_by_transcript,
        )

        for process_group in sorted(process_groups, key=lambda item: item.display_order):
            group_steps: list[StepRecord] = []
            group_notes: list[NoteRecord] = []
            for transcript in transcripts_by_group.get(process_group.id, []):
                transcript_steps = [cast(StepRecord, dict(step)) for step in steps_by_transcript.get(transcript.id, [])]
                transcript_notes = [cast(NoteRecord, dict(note)) for note in notes_by_transcript.get(transcript.id, [])]
                group_steps = merge_steps(group_steps, transcript_steps)
                group_notes = merge_notes(group_notes, transcript_notes)

            canonical_steps.extend(group_steps)
            canonical_notes.extend(group_notes)

        for step_number, step in enumerate(canonical_steps, start=1):
            step["step_number"] = step_number

        for step in canonical_steps:
            transcript_id = step_transcript_id(step)
            if transcript_id is None:
                continue
            merged_steps_by_transcript.setdefault(transcript_id, []).append(step)

        for note in canonical_notes:
            transcript_id = note_transcript_id(note)
            if transcript_id is None:
                continue
            merged_notes_by_transcript.setdefault(transcript_id, []).append(note)

        return CanonicalMergeResult(
            steps=canonical_steps,
            notes=canonical_notes,
            steps_by_transcript=merged_steps_by_transcript,
            notes_by_transcript=merged_notes_by_transcript,
        )

