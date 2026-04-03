from __future__ import annotations

from typing import Protocol

from worker.services.draft_generation.support import (
    SCREENSHOT_ROLE_LOCAL_OFFSETS,
    SCREENSHOT_ROLE_ORDER,
    classify_action_type,
    seconds_to_timestamp,
    timestamp_to_seconds,
)
from worker.services.generation_types import DerivedScreenshotRecord, ScreenshotCandidateRecord, StepRecord
from worker.services.media.video_frame_extractor import ExtractedFrameCandidate


class ScreenshotSelectionSettings(Protocol):
    screenshot_selected_count: int


def select_screenshot_roles(step: StepRecord) -> list[str]:
    span_seconds = max(
        0,
        timestamp_to_seconds(step.get("end_timestamp") or step.get("timestamp") or "00:00:01")
        - timestamp_to_seconds(step.get("start_timestamp") or step.get("timestamp") or "00:00:01"),
    )
    action_type = classify_action_type(step.get("action_text", ""))
    if span_seconds <= 2:
        return ["during"]
    if span_seconds <= 6:
        if action_type in {"navigate", "submit"}:
            return ["before", "after"]
        return ["during", "after"]
    return list(SCREENSHOT_ROLE_ORDER)


def apply_selected_limit(settings: ScreenshotSelectionSettings, roles: list[str]) -> list[str]:
    if not roles:
        return []
    max_selected = max(1, settings.screenshot_selected_count)
    if max_selected >= len(roles):
        return roles
    if max_selected == 1:
        return ["during"] if "during" in roles else [roles[-1]]
    if max_selected == 2:
        if "before" in roles and "after" in roles and "during" not in roles:
            return ["before", "after"]
        prioritized = [role for role in ("during", "after", "before") if role in roles]
        return prioritized[:2]
    prioritized = [role for role in ("before", "during", "after") if role in roles]
    return prioritized[:max_selected]


def timestamp_for_role(step: StepRecord, role: str) -> str:
    start_seconds = timestamp_to_seconds(step.get("start_timestamp") or step.get("timestamp") or "00:00:01")
    end_seconds = max(start_seconds, timestamp_to_seconds(step.get("end_timestamp") or step.get("timestamp") or "00:00:01"))
    if role == "before":
        return seconds_to_timestamp(start_seconds)
    if role == "after":
        return seconds_to_timestamp(end_seconds)
    midpoint = start_seconds + ((end_seconds - start_seconds) // 2)
    return seconds_to_timestamp(midpoint)


def candidate_timestamps_for_role(base_timestamp: str, role: str) -> list[str]:
    base_seconds = timestamp_to_seconds(base_timestamp)
    offsets = SCREENSHOT_ROLE_LOCAL_OFFSETS.get(role, [0])
    points = [max(1, base_seconds + offset) for offset in offsets]
    ordered: list[int] = []
    seen: set[int] = set()
    for point in points:
        if point in seen:
            continue
        seen.add(point)
        ordered.append(point)
    return [seconds_to_timestamp(point) for point in ordered]


def score_candidate(action_type: str, candidate: ExtractedFrameCandidate, step: StepRecord) -> float:
    quality_score = min(candidate.file_size / 10_000, 10.0)
    display_seconds = timestamp_to_seconds(step.get("timestamp") or candidate.timestamp)
    start_seconds = timestamp_to_seconds(step.get("start_timestamp") or step.get("timestamp") or candidate.timestamp)
    end_seconds = timestamp_to_seconds(step.get("end_timestamp") or step.get("timestamp") or candidate.timestamp)
    candidate_seconds = timestamp_to_seconds(candidate.timestamp)
    timing_penalty = abs(candidate_seconds - display_seconds)
    score = quality_score - timing_penalty
    if start_seconds <= candidate_seconds <= end_seconds:
        score += 3.0
    if action_type == "navigate" and candidate.offset_seconds >= 1:
        score += 2.5
    elif action_type == "data_entry" and 0 <= candidate.offset_seconds <= 2:
        score += 2.5
    elif action_type == "copy" and -2 <= candidate.offset_seconds <= 0:
        score += 2.0
    elif action_type == "submit" and candidate.offset_seconds >= 1:
        score += 2.5
    elif action_type == "default" and -1 <= candidate.offset_seconds <= 2:
        score += 1.5
    if candidate.file_size < 4_000:
        score -= 3.0
    return score


def select_best_candidate_record(step: StepRecord, candidates: list[ScreenshotCandidateRecord]) -> ScreenshotCandidateRecord | None:
    if not candidates:
        return None
    action_type = classify_action_type(step.get("action_text", ""))
    best_candidate: ScreenshotCandidateRecord | None = None
    best_score = float("-inf")
    for candidate in candidates:
        frame_candidate = ExtractedFrameCandidate(
            output_path=candidate["artifact"].storage_path,
            timestamp=candidate["timestamp"],
            offset_seconds=candidate.get("offset_seconds", 0),
            file_size=candidate.get("file_size", candidate["artifact"].size_bytes),
        )
        score = score_candidate(action_type, frame_candidate, step)
        if score > best_score:
            best_score = score
            best_candidate = candidate
    return best_candidate


def select_step_screenshot_slots(
    settings: ScreenshotSelectionSettings,
    *,
    step: StepRecord,
    candidate_screenshots: list[ScreenshotCandidateRecord],
) -> list[DerivedScreenshotRecord]:
    if not candidate_screenshots:
        return []
    roles = apply_selected_limit(settings, select_screenshot_roles(step))
    screenshots: list[DerivedScreenshotRecord] = []
    used_artifact_ids: set[str] = set()
    for sequence_number, role in enumerate(roles, start=1):
        target_timestamp = timestamp_for_role(step, role)
        candidate_timestamp_set = set(candidate_timestamps_for_role(target_timestamp, role))
        scoped_candidates = [
            candidate
            for candidate in candidate_screenshots
            if candidate["artifact"].id not in used_artifact_ids and candidate["timestamp"] in candidate_timestamp_set
        ]
        if not scoped_candidates:
            scoped_candidates = [candidate for candidate in candidate_screenshots if candidate["artifact"].id not in used_artifact_ids]
        best_candidate = select_best_candidate_record(step, scoped_candidates)
        if best_candidate is None:
            continue
        used_artifact_ids.add(best_candidate["artifact"].id)
        screenshots.append(
            {
                "artifact": best_candidate["artifact"],
                "role": role,
                "sequence_number": sequence_number,
                "timestamp": best_candidate["timestamp"],
                "selection_method": "span-sequence",
                "is_primary": role == "during" or (role == roles[0] and "during" not in roles),
            }
        )
    if screenshots and not any(item["is_primary"] for item in screenshots):
        screenshots[0]["is_primary"] = True
    return screenshots
