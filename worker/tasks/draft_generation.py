r"""
Purpose: Background task for long-running draft generation work.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\tasks\draft_generation.py
"""

from worker.celery_app import celery_app
from worker.services.draft_generation_worker import DraftGenerationWorker


@celery_app.task(name="draft_generation.run", bind=True, autoretry_for=(RuntimeError,), retry_backoff=True, max_retries=3)
def run_draft_generation(self, session_id: str) -> dict[str, int | str]:
    """Run the draft generation pipeline in the background."""
    worker = DraftGenerationWorker()
    try:
        return worker.run(session_id)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
