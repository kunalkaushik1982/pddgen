"""
Tests for optional-video behaviour.

Video upload is intentionally optional as of the feature/optional-video branch.
When absent, _has_required_uploads still returns True and the worker's screenshot
derivation stage is expected to skip gracefully (tested at the worker level).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.draft_session.mappers import _has_required_uploads


# ---------------------------------------------------------------------------
# Helper: build a minimal mock DraftSessionModel with the given artifact kinds
# ---------------------------------------------------------------------------

def _make_session(*kinds: str):
    artifacts = [SimpleNamespace(kind=k) for k in kinds]
    return SimpleNamespace(artifacts=artifacts)


# ---------------------------------------------------------------------------
# _has_required_uploads — unit tests
# ---------------------------------------------------------------------------


class TestHasRequiredUploads:
    """Video is now optional — only transcript + template are required."""

    def test_transcript_and_template_only_is_ready(self):
        """Session with transcript + template but NO video should be resume-ready."""
        session = _make_session("transcript", "template")
        assert _has_required_uploads(session) is True

    def test_all_three_still_ready(self):
        """Session with video + transcript + template remains resume-ready."""
        session = _make_session("video", "transcript", "template")
        assert _has_required_uploads(session) is True

    def test_missing_transcript_is_not_ready(self):
        """Without a transcript the session is never ready, even with video."""
        session = _make_session("video", "template")
        assert _has_required_uploads(session) is False

    def test_missing_template_is_not_ready(self):
        """Without a template the session is never ready."""
        session = _make_session("video", "transcript")
        assert _has_required_uploads(session) is False

    def test_video_only_is_not_ready(self):
        """A session with only a video cannot start generation."""
        session = _make_session("video")
        assert _has_required_uploads(session) is False

    def test_empty_artifacts_is_not_ready(self):
        """A session with no artifacts is not ready."""
        session = _make_session()
        assert _has_required_uploads(session) is False

    def test_multiple_transcripts_and_template_is_ready(self):
        """Multiple transcripts + a template (no video) is still ready."""
        session = _make_session("transcript", "transcript", "template")
        assert _has_required_uploads(session) is True

    def test_extra_kinds_do_not_block(self):
        """Presence of sop / diagram / screenshot kinds does not affect the check."""
        session = _make_session("transcript", "template", "sop", "diagram", "screenshot")
        assert _has_required_uploads(session) is True
