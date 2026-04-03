from __future__ import annotations

from app.core.observability import bind_log_context, get_logger

from app.models.action_log import ActionLogModel
from worker.services.orchestration.contracts import WorkerDbSession

logger = get_logger(__name__)


class FailureStage:
    """Persist failure state for background generation errors."""

    @staticmethod
    def mark_failed(db: WorkerDbSession, session_id: str, detail: str | None = None) -> None:
        from app.models.draft_session import DraftSessionModel

        with bind_log_context(stage="failure"):
            session = db.get(DraftSessionModel, session_id)
            if session is None:
                return
            session.status = "failed"
            failure_detail = (detail or "Background draft generation did not complete successfully.").strip()
            if len(failure_detail) > 500:
                failure_detail = f"{failure_detail[:497]}..."
            db.add(
                ActionLogModel(
                    session_id=session_id,
                    event_type="generation_failed",
                    title="Draft generation failed",
                    detail=failure_detail,
                    actor="system",
                )
            )
            db.commit()
            logger.error(
                "Failure stage persisted draft generation error",
                extra={"event": "draft_generation.stage_failed", "failure_detail": failure_detail},
            )
