from __future__ import annotations

from worker.pipeline.stages.support import seconds_to_timestamp, timestamp_to_seconds
from worker.pipeline.types import StepRecord


def window_sampling_is_reliable(step: StepRecord, *, max_window_seconds: int) -> bool:
    start_timestamp = str(step.get("start_timestamp") or "").strip()
    end_timestamp = str(step.get("end_timestamp") or "").strip()
    display_timestamp = str(step.get("timestamp") or "").strip()
    if not start_timestamp or not end_timestamp:
        return False
    start_seconds = timestamp_to_seconds(start_timestamp)
    end_seconds = timestamp_to_seconds(end_timestamp)
    if end_seconds < start_seconds:
        return False
    span_seconds = end_seconds - start_seconds
    if span_seconds <= 0 or span_seconds > max_window_seconds:
        return False
    if not step.get("evidence_references"):
        return False
    if display_timestamp:
        display_seconds = timestamp_to_seconds(display_timestamp)
        if not start_seconds <= display_seconds <= end_seconds:
            return False
    return True


def split_timestamp_parts(value: str) -> tuple[int, int, int] | None:
    parts = str(value or "").split(":")
    if len(parts) != 3:
        return None
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None


def coerce_seconds_for_video(timestamp_value: str, *, video_duration_seconds: int | None) -> int:
    parsed_seconds = timestamp_to_seconds(timestamp_value or "00:00:01")
    if not video_duration_seconds or parsed_seconds <= video_duration_seconds:
        return parsed_seconds
    parts = split_timestamp_parts(timestamp_value)
    if parts is not None:
        first, second, third = parts
        if third == 0:
            recovered_mmss_seconds = (first * 60) + second
            if 1 <= recovered_mmss_seconds <= video_duration_seconds:
                return recovered_mmss_seconds
    return video_duration_seconds


def effective_span_seconds(step: StepRecord, *, video_duration_seconds: int | None, max_window_seconds: int) -> tuple[bool, int, int, int, int]:
    fallback_timestamp = step.get("timestamp") or "00:00:01"
    start_seconds = coerce_seconds_for_video(step.get("start_timestamp") or fallback_timestamp, video_duration_seconds=video_duration_seconds)
    end_seconds = max(start_seconds, coerce_seconds_for_video(step.get("end_timestamp") or fallback_timestamp, video_duration_seconds=video_duration_seconds))
    display_seconds = coerce_seconds_for_video(fallback_timestamp, video_duration_seconds=video_duration_seconds)
    return (
        window_sampling_is_reliable(step, max_window_seconds=max_window_seconds),
        max(0, end_seconds - start_seconds),
        start_seconds,
        end_seconds,
        display_seconds,
    )


def ordered_unique_points(points: list[int]) -> list[int]:
    ordered: list[int] = []
    seen: set[int] = set()
    for point in points:
        normalized = max(1, point)
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def fill_points_to_limit(base_points: list[int], *, anchor_seconds: int, limit: int, anchor_padding_seconds: int) -> list[int]:
    ordered = ordered_unique_points(base_points)
    if len(ordered) >= limit:
        return ordered[:limit]
    padding = max(1, anchor_padding_seconds)
    step_distance = 1
    while len(ordered) < limit:
        for direction in (-1, 1):
            candidate = anchor_seconds + (direction * padding * step_distance)
            candidate_points = ordered_unique_points(ordered + [candidate])
            if len(candidate_points) != len(ordered):
                ordered = candidate_points
            if len(ordered) >= limit:
                break
        step_distance += 1
    return ordered[:limit]


def practical_candidate_limit(
    *,
    reliable_window: bool,
    span_seconds: int,
    candidate_count: int,
    anchor_candidate_cap: int,
    short_window_seconds: int,
    short_window_candidate_cap: int,
    medium_window_seconds: int,
    medium_window_candidate_cap: int,
    long_window_seconds: int,
    long_window_candidate_cap: int,
    extended_window_candidate_cap: int,
) -> int:
    configured_max = max(1, candidate_count)
    if not reliable_window:
        return min(configured_max, max(1, anchor_candidate_cap))
    if span_seconds <= short_window_seconds:
        return min(configured_max, max(1, short_window_candidate_cap))
    if span_seconds <= medium_window_seconds:
        return min(configured_max, max(1, medium_window_candidate_cap))
    if span_seconds <= long_window_seconds:
        return min(configured_max, max(1, long_window_candidate_cap))
    return min(configured_max, max(1, extended_window_candidate_cap))


def candidate_seconds_for_step(step: StepRecord, *, video_duration_seconds: int | None, settings) -> list[int]:  # type: ignore[no-untyped-def]
    reliable_window, span_seconds, start_seconds, end_seconds, display_seconds = effective_span_seconds(
        step,
        video_duration_seconds=video_duration_seconds,
        max_window_seconds=settings.screenshot_window_max_seconds,
    )
    limit = practical_candidate_limit(
        reliable_window=reliable_window,
        span_seconds=span_seconds,
        candidate_count=settings.screenshot_candidate_count,
        anchor_candidate_cap=settings.screenshot_anchor_candidate_cap,
        short_window_seconds=settings.screenshot_short_window_seconds,
        short_window_candidate_cap=settings.screenshot_short_window_candidate_cap,
        medium_window_seconds=settings.screenshot_medium_window_seconds,
        medium_window_candidate_cap=settings.screenshot_medium_window_candidate_cap,
        long_window_seconds=settings.screenshot_long_window_seconds,
        long_window_candidate_cap=settings.screenshot_long_window_candidate_cap,
        extended_window_candidate_cap=settings.screenshot_extended_window_candidate_cap,
    )
    if reliable_window:
        midpoint = start_seconds + ((end_seconds - start_seconds) // 2)
        return fill_points_to_limit(
            [start_seconds, midpoint, end_seconds],
            anchor_seconds=midpoint,
            limit=limit,
            anchor_padding_seconds=settings.screenshot_anchor_padding_seconds,
        )
    anchor_seconds = display_seconds or start_seconds or end_seconds
    return fill_points_to_limit(
        [anchor_seconds],
        anchor_seconds=anchor_seconds,
        limit=limit,
        anchor_padding_seconds=settings.screenshot_anchor_padding_seconds,
    )


def build_candidate_timestamps(step: StepRecord, *, video_duration_seconds: int | None, settings) -> list[str]:  # type: ignore[no-untyped-def]
    return [
        seconds_to_timestamp(point)
        for point in candidate_seconds_for_step(step, video_duration_seconds=video_duration_seconds, settings=settings)
    ]
