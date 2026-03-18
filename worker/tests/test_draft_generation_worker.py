from __future__ import annotations

from unittest.mock import Mock, patch
import unittest

from worker.services.draft_generation_worker import DraftGenerationWorker


class DraftGenerationWorkerTests(unittest.TestCase):
    @patch("worker.services.draft_generation_worker.get_db_session")
    def test_runs_generation_stages_in_order(self, get_db_session_mock) -> None:
        db = Mock()
        get_db_session_mock.return_value = db

        worker = DraftGenerationWorker(task_id="task-1")
        order: list[str] = []
        context = object()

        worker._load_session = Mock(side_effect=lambda _db, _session_id: order.append("load_session") or "session")
        worker.session_preparation_stage.load_and_prepare = Mock(
            side_effect=lambda _db, _session: order.append("prepare") or context
        )
        worker.transcript_stage.run = Mock(side_effect=lambda _db, _context: order.append("transcript"))
        worker.screenshot_stage.run = Mock(side_effect=lambda _db, _context: order.append("screenshots"))
        worker.diagram_stage.run = Mock(side_effect=lambda _db, _context: order.append("diagram"))
        worker.persistence_stage.run = Mock(
            side_effect=lambda _db, _context: order.append("persist") or {"session_id": "session-1", "steps_created": 2}
        )

        result = worker.run("session-1")

        assert order == ["load_session", "prepare", "transcript", "screenshots", "diagram", "persist"]
        assert result["session_id"] == "session-1"
        db.close.assert_called_once()

    @patch("worker.services.draft_generation_worker.get_db_session")
    def test_marks_failure_when_stage_raises(self, get_db_session_mock) -> None:
        db = Mock()
        get_db_session_mock.return_value = db

        worker = DraftGenerationWorker(task_id="task-2")
        worker._load_session = Mock(return_value="session")
        worker.session_preparation_stage.load_and_prepare = Mock(return_value="context")
        worker.transcript_stage.run = Mock(side_effect=RuntimeError("boom"))
        worker.failure_stage.mark_failed = Mock()

        with self.assertRaises(RuntimeError):
            worker.run("session-2")

        worker.failure_stage.mark_failed.assert_called_once_with(db, "session-2", "boom")
        db.close.assert_called_once()
