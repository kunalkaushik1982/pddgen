"""Unit tests for generation wall-time helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.platform.generation_timing import wall_duration_seconds


def test_wall_duration_seconds_returns_none_if_incomplete() -> None:
    assert wall_duration_seconds(None, datetime.now(timezone.utc)) is None
    assert wall_duration_seconds(datetime.now(timezone.utc), None) is None


def test_wall_duration_seconds_computes_elapsed() -> None:
    start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(seconds=125)
    assert wall_duration_seconds(start, end) == 125.0


def test_wall_duration_seconds_normalizes_naive_as_utc() -> None:
    start = datetime(2026, 1, 1, 12, 0, 0)
    end = datetime(2026, 1, 1, 12, 0, 30)
    assert wall_duration_seconds(start, end) == 30.0
