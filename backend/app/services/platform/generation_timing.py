r"""
Wall-clock boundaries for background draft and screenshot generation jobs.

Single responsibility: persist started_at / completed_at on the draft session row.
Tasks orchestrate timing via context managers without embedding SQL in Celery modules.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.models.draft_session import DraftSessionModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def wall_duration_seconds(started_at: datetime | None, completed_at: datetime | None) -> float | None:
    """Return elapsed seconds between boundaries, or None if either is missing."""
    if started_at is None or completed_at is None:
        return None
    start = started_at if started_at.tzinfo is not None else started_at.replace(tzinfo=timezone.utc)
    end = completed_at if completed_at.tzinfo is not None else completed_at.replace(tzinfo=timezone.utc)
    return max(0.0, (end - start).total_seconds())


class GenerationTimingRecorder:
    """Persists generation wall-time boundaries for one draft session (ORM row)."""

    __slots__ = ("_db",)

    def __init__(self, db: Session) -> None:
        self._db = db

    def mark_draft_generation_started(self, session_id: str) -> None:
        row = self._db.get(DraftSessionModel, session_id)
        if row is None:
            return
        row.draft_generation_started_at = utcnow()
        row.draft_generation_completed_at = None
        self._db.commit()

    def mark_draft_generation_finished(self, session_id: str) -> None:
        row = self._db.get(DraftSessionModel, session_id)
        if row is None:
            return
        row.draft_generation_completed_at = utcnow()
        self._db.commit()

    def mark_screenshot_generation_started(self, session_id: str) -> None:
        row = self._db.get(DraftSessionModel, session_id)
        if row is None:
            return
        row.screenshot_generation_started_at = utcnow()
        row.screenshot_generation_completed_at = None
        self._db.commit()

    def mark_screenshot_generation_finished(self, session_id: str) -> None:
        row = self._db.get(DraftSessionModel, session_id)
        if row is None:
            return
        row.screenshot_generation_completed_at = utcnow()
        self._db.commit()


@contextmanager
def track_draft_generation_wall_time(
    session_id: str,
    *,
    session_factory: Callable[[], Session] | None = None,
) -> Iterator[None]:
    """Mark draft generation start; always mark completion when the block exits (success or error)."""
    from app.db.session import SessionLocal

    factory = session_factory or SessionLocal
    db = factory()
    try:
        GenerationTimingRecorder(db).mark_draft_generation_started(session_id)
    finally:
        db.close()
    try:
        yield
    finally:
        db = factory()
        try:
            GenerationTimingRecorder(db).mark_draft_generation_finished(session_id)
        finally:
            db.close()


@contextmanager
def track_screenshot_generation_wall_time(
    session_id: str,
    *,
    session_factory: Callable[[], Session] | None = None,
) -> Iterator[None]:
    """Mark screenshot generation start; always mark completion when the block exits (success or error)."""
    from app.db.session import SessionLocal

    factory = session_factory or SessionLocal
    db = factory()
    try:
        GenerationTimingRecorder(db).mark_screenshot_generation_started(session_id)
    finally:
        db.close()
    try:
        yield
    finally:
        db = factory()
        try:
            GenerationTimingRecorder(db).mark_screenshot_generation_finished(session_id)
        finally:
            db.close()
