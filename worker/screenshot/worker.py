r"""
Purpose: Background worker for screenshot-only generation over persisted canonical steps.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\screenshot_generation_worker.py
"""

from __future__ import annotations

from worker import bootstrap as _bootstrap  # noqa: F401
from app.core.observability import bind_log_context, get_logger
from worker.pipeline.composition import build_screenshot_generation_use_case

logger = get_logger(__name__)


class ScreenshotGenerationWorker:
    """Compatibility adapter over the screenshot generation use case."""

    def __init__(self, task_id: str | None = None, use_case=None) -> None:
        self.task_id = task_id
        self._use_case = use_case or build_screenshot_generation_use_case(task_id=task_id)

    def run(self, session_id: str) -> dict[str, int | str]:
        """Generate screenshots only for persisted canonical steps."""
        with bind_log_context(task_id=self.task_id, session_id=session_id):
            result = self._use_case.run(session_id=session_id)
            logger.info("Persisted generated screenshots", extra={"event": "screenshot_generation.persisted", **result})
            return result
