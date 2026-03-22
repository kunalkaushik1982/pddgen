r"""
Purpose: Deterministic canonical merge for multi-meeting draft generation.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\canonical_process_merge.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.models.artifact import ArtifactModel
from app.models.process_group import ProcessGroupModel


@dataclass(slots=True)
class CanonicalMergeResult:
    """Return the canonicalized process state after merging meeting evidence."""

    steps: list[dict]
    notes: list[dict]
    steps_by_transcript: dict[str, list[dict]]
    notes_by_transcript: dict[str, list[dict]]


class CanonicalProcessMergeService:
    """Build one current process view from multiple meeting-specific transcript outputs."""

    _STOPWORDS = {
        "a",
        "an",
        "and",
        "the",
        "to",
        "of",
        "for",
        "in",
        "on",
        "with",
        "into",
        "from",
        "then",
        "after",
        "before",
        "click",
        "select",
        "enter",
        "open",
        "go",
        "navigate",
    }

    def merge(
        self,
        *,
        transcript_artifacts: list[ArtifactModel],
        process_groups: list[ProcessGroupModel],
        steps_by_transcript: dict[str, list[dict]],
        notes_by_transcript: dict[str, list[dict]],
    ) -> CanonicalMergeResult:
        """Apply a latest-wins merge within each process group and append groups in display order."""
        canonical_steps: list[dict] = []
        canonical_notes: list[dict] = []
        merged_steps_by_transcript: dict[str, list[dict]] = {}
        merged_notes_by_transcript: dict[str, list[dict]] = {}

        transcripts_by_group = self._group_transcripts_by_process_group(
            transcript_artifacts=transcript_artifacts,
            steps_by_transcript=steps_by_transcript,
            notes_by_transcript=notes_by_transcript,
        )

        for process_group in sorted(process_groups, key=lambda item: item.display_order):
            group_steps: list[dict] = []
            group_notes: list[dict] = []
            for transcript in transcripts_by_group.get(process_group.id, []):
                transcript_steps = [dict(step) for step in steps_by_transcript.get(transcript.id, [])]
                transcript_notes = [dict(note) for note in notes_by_transcript.get(transcript.id, [])]
                group_steps = self._merge_steps(group_steps, transcript_steps)
                group_notes = self._merge_notes(group_notes, transcript_notes)

            canonical_steps.extend(group_steps)
            canonical_notes.extend(group_notes)

        for step_number, step in enumerate(canonical_steps, start=1):
            step["step_number"] = step_number

        for step in canonical_steps:
            transcript_id = self._step_transcript_id(step)
            if transcript_id is None:
                continue
            merged_steps_by_transcript.setdefault(transcript_id, []).append(step)

        for note in canonical_notes:
            transcript_id = self._note_transcript_id(note)
            if transcript_id is None:
                continue
            merged_notes_by_transcript.setdefault(transcript_id, []).append(note)

        return CanonicalMergeResult(
            steps=canonical_steps,
            notes=canonical_notes,
            steps_by_transcript=merged_steps_by_transcript,
            notes_by_transcript=merged_notes_by_transcript,
        )

    def _group_transcripts_by_process_group(
        self,
        *,
        transcript_artifacts: list[ArtifactModel],
        steps_by_transcript: dict[str, list[dict]],
        notes_by_transcript: dict[str, list[dict]],
    ) -> dict[str, list[ArtifactModel]]:
        grouped: dict[str, list[ArtifactModel]] = {}
        for transcript in self._sort_transcripts(transcript_artifacts):
            process_group_id = self._transcript_process_group_id(
                transcript.id,
                steps_by_transcript=steps_by_transcript,
                notes_by_transcript=notes_by_transcript,
            )
            if process_group_id is None:
                continue
            grouped.setdefault(process_group_id, []).append(transcript)
        return grouped

    def _merge_steps(self, canonical_steps: list[dict], transcript_steps: list[dict]) -> list[dict]:
        if not canonical_steps:
            return list(transcript_steps)
        if not transcript_steps:
            return list(canonical_steps)

        matched_canonical_indexes = self._match_step_indexes(canonical_steps, transcript_steps)
        result: list[dict] = []
        pending_inserts: list[dict] = []
        canonical_cursor = 0
        has_seen_match = False

        for step_index, transcript_step in enumerate(transcript_steps):
            matched_index = matched_canonical_indexes.get(step_index)
            if matched_index is None:
                pending_inserts.append(transcript_step)
                continue

            if has_seen_match:
                result.extend(pending_inserts)
                result.extend(canonical_steps[canonical_cursor:matched_index])
            else:
                result.extend(canonical_steps[canonical_cursor:matched_index])
                result.extend(pending_inserts)
            pending_inserts = []
            result.append(transcript_step)
            canonical_cursor = matched_index + 1
            has_seen_match = True

        result.extend(canonical_steps[canonical_cursor:])
        result.extend(pending_inserts)
        return result

    def _merge_notes(self, canonical_notes: list[dict], transcript_notes: list[dict]) -> list[dict]:
        merged = list(canonical_notes)
        for note in transcript_notes:
            normalized_text = self._normalize_text(str(note.get("text", "")))
            matched_index = next(
                (
                    index
                    for index, existing in enumerate(merged)
                    if self._normalize_text(str(existing.get("text", ""))) == normalized_text
                ),
                None,
            )
            if matched_index is None:
                merged.append(note)
                continue
            merged[matched_index] = note
        return merged

    def _match_step_indexes(self, canonical_steps: list[dict], transcript_steps: list[dict]) -> dict[int, int]:
        used_canonical_indexes: set[int] = set()
        matches: dict[int, int] = {}
        for transcript_index, transcript_step in enumerate(transcript_steps):
            best_index: int | None = None
            best_score = 0.0
            for canonical_index, canonical_step in enumerate(canonical_steps):
                if canonical_index in used_canonical_indexes:
                    continue
                score = self._step_similarity(canonical_step, transcript_step)
                if score > best_score:
                    best_score = score
                    best_index = canonical_index
            if best_index is not None and best_score >= 0.78:
                matches[transcript_index] = best_index
                used_canonical_indexes.add(best_index)
        return matches

    def _step_similarity(self, left: dict, right: dict) -> float:
        left_action = self._normalize_text(str(left.get("action_text", "")))
        right_action = self._normalize_text(str(right.get("action_text", "")))
        if not left_action or not right_action:
            return 0.0

        action_ratio = SequenceMatcher(None, left_action, right_action).ratio()
        left_tokens = self._tokenize(left_action)
        right_tokens = self._tokenize(right_action)
        token_overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)

        left_app = self._normalize_text(str(left.get("application_name", "")))
        right_app = self._normalize_text(str(right.get("application_name", "")))
        app_score = 1.0 if left_app and left_app == right_app else 0.0

        return (action_ratio * 0.6) + (token_overlap * 0.25) + (app_score * 0.15)

    def _sort_transcripts(self, transcript_artifacts: list[ArtifactModel]) -> list[ArtifactModel]:
        return sorted(transcript_artifacts, key=self._transcript_sort_key)

    def _transcript_sort_key(self, artifact: ArtifactModel) -> tuple[int, str, str, str]:
        meeting = getattr(artifact, "meeting", None)
        order_index = getattr(meeting, "order_index", None)
        meeting_date = getattr(meeting, "meeting_date", None)
        uploaded_at = getattr(meeting, "uploaded_at", None) or getattr(artifact, "created_at", None)
        return (
            order_index if order_index is not None else 1_000_000,
            meeting_date.isoformat() if meeting_date is not None else "",
            uploaded_at.isoformat() if uploaded_at is not None else "",
            artifact.id,
        )

    @staticmethod
    def _step_transcript_id(step: dict) -> str | None:
        transcript_id = step.get("_transcript_artifact_id")
        return transcript_id if isinstance(transcript_id, str) and transcript_id else None

    @staticmethod
    def _note_transcript_id(note: dict) -> str | None:
        transcript_id = note.get("_transcript_artifact_id")
        return transcript_id if isinstance(transcript_id, str) and transcript_id else None

    @staticmethod
    def _transcript_process_group_id(
        transcript_id: str,
        *,
        steps_by_transcript: dict[str, list[dict]],
        notes_by_transcript: dict[str, list[dict]],
    ) -> str | None:
        for step in steps_by_transcript.get(transcript_id, []):
            process_group_id = step.get("process_group_id")
            if isinstance(process_group_id, str) and process_group_id:
                return process_group_id
        for note in notes_by_transcript.get(transcript_id, []):
            process_group_id = note.get("process_group_id")
            if isinstance(process_group_id, str) and process_group_id:
                return process_group_id
        return None

    def _tokenize(self, value: str) -> set[str]:
        return {token for token in self._normalize_text(value).split() if token and token not in self._STOPWORDS}

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
        return re.sub(r"\s+", " ", normalized).strip()
