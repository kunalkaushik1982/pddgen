r"""
Purpose: Background draft-generation coordinator for transcript normalization and screenshot derivation.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\draft_generation_worker.py
"""

from worker import bootstrap as _bootstrap  # noqa: F401
from app.core.observability import bind_log_context, get_logger
from worker.services.worker_composition import build_draft_generation_use_case

logger = get_logger(__name__)


class DraftGenerationWorker:
    """Compatibility adapter over the draft generation use case."""

    def __init__(self, task_id: str | None = None, use_case=None) -> None:
        self.task_id = task_id
        self._use_case = use_case or build_draft_generation_use_case(task_id=task_id)

    def run(self, session_id: str) -> dict[str, int | str]:
        """Generate draft steps, notes, and derived screenshots for a session."""
        with bind_log_context(task_id=self.task_id, session_id=session_id):
            result = self._use_case.run(session_id=session_id)
            logger.info("Persisted generated draft artifacts", extra={"event": "draft_generation.persisted", **result})
            return result
