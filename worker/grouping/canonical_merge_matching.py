from __future__ import annotations

import re
from difflib import SequenceMatcher

from worker.pipeline.types import NoteRecord, StepRecord

STOPWORDS = {
    "a","an","and","the","to","of","for","in","on","with","into","from","then","after","before","click","select","enter","open","go","navigate",
}


def merge_steps(canonical_steps: list[StepRecord], transcript_steps: list[StepRecord]) -> list[StepRecord]:
    if not canonical_steps:
        return list(transcript_steps)
    if not transcript_steps:
        return list(canonical_steps)
    matched_canonical_indexes = match_step_indexes(canonical_steps, transcript_steps)
    result: list[StepRecord] = []
    pending_inserts: list[StepRecord] = []
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


def merge_notes(canonical_notes: list[NoteRecord], transcript_notes: list[NoteRecord]) -> list[NoteRecord]:
    merged = list(canonical_notes)
    for note in transcript_notes:
        normalized_text = normalize_text(str(note.get("text", "")))
        matched_index = next((index for index, existing in enumerate(merged) if normalize_text(str(existing.get("text", ""))) == normalized_text), None)
        if matched_index is None:
            merged.append(note)
            continue
        merged[matched_index] = note
    return merged


def match_step_indexes(canonical_steps: list[StepRecord], transcript_steps: list[StepRecord]) -> dict[int, int]:
    used_canonical_indexes: set[int] = set()
    matches: dict[int, int] = {}
    for transcript_index, transcript_step in enumerate(transcript_steps):
        best_index: int | None = None
        best_score = 0.0
        for canonical_index, canonical_step in enumerate(canonical_steps):
            if canonical_index in used_canonical_indexes:
                continue
            score = step_similarity(canonical_step, transcript_step)
            if score > best_score:
                best_score = score
                best_index = canonical_index
        if best_index is not None and best_score >= 0.78:
            matches[transcript_index] = best_index
            used_canonical_indexes.add(best_index)
    return matches


def step_similarity(left: StepRecord, right: StepRecord) -> float:
    left_action = normalize_text(str(left.get("action_text", "")))
    right_action = normalize_text(str(right.get("action_text", "")))
    if not left_action or not right_action:
        return 0.0
    action_ratio = SequenceMatcher(None, left_action, right_action).ratio()
    left_tokens = tokenize(left_action)
    right_tokens = tokenize(right_action)
    token_overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    left_app = normalize_text(str(left.get("application_name", "")))
    right_app = normalize_text(str(right.get("application_name", "")))
    app_score = 1.0 if left_app and left_app == right_app else 0.0
    return (action_ratio * 0.6) + (token_overlap * 0.25) + (app_score * 0.15)


def tokenize(value: str) -> set[str]:
    return {token for token in normalize_text(value).split() if token and token not in STOPWORDS}


def normalize_text(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()
