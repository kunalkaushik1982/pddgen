from __future__ import annotations

import re
from typing import Any


def normalize_confidence(value: Any) -> str:
    normalized = str(value or "medium").lower()
    return normalized if normalized in {"high", "medium", "low", "unknown"} else "medium"


def confidence_rank(confidence: str) -> int:
    return {"unknown": 0, "low": 1, "medium": 2, "high": 3}.get(confidence, 1)


def confidence_from_rank(rank: int) -> str:
    return {0: "unknown", 1: "low", 2: "medium", 3: "high"}.get(max(0, min(rank, 3)), "low")


def calibrate_confidence(confidence: str, *, evidence_points: int, quality_points: int, lower_when: int = 2) -> str:
    rank = confidence_rank(confidence)
    if evidence_points <= lower_when:
        rank = min(rank, 1)
    elif evidence_points <= lower_when + 1 and rank > 1:
        rank -= 1
    if quality_points <= 0:
        rank = min(rank, 1)
    elif quality_points == 1 and rank > 1:
        rank -= 1
    return confidence_from_rank(rank)


def workflow_evidence_points(workflow_summary: dict[str, Any]) -> int:
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


def title_quality_points(workflow_title: str) -> int:
    token_count = len([token for token in re.split(r"\s+", workflow_title.strip()) if token])
    if token_count < 2:
        return 0
    if token_count <= 6:
        return 2
    return 1


def summary_quality_points(summary_text: str) -> int:
    sentence_count = len([part for part in re.split(r"[.!?]+", summary_text) if part.strip()])
    if sentence_count < 2:
        return 0
    if sentence_count <= 4:
        return 2
    return 1
