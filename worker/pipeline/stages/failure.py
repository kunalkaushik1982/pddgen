from __future__ import annotations

from app.core.observability import bind_log_context, get_logger

from app.models.action_log import ActionLogModel

logger = get_logger(__name__)


class FailureStage:
    """Persist failure state for background generation errors."""

    @staticmethod
    def mark_failed(
        db,  # type: ignore[no-untyped-def]
        session_id: str,
        detail: str | None = None,
        *,
        title: str = "Draft generation failed",
        failure_event_type: str = "generation_failed",
        terminal_status: str = "failed",
        log_event: str = "draft_generation.stage_failed",
    ) -> None:
        from app.models.draft_session import DraftSessionModel

        with bind_log_context(stage="failure"):
            session = db.get(DraftSessionModel, session_id)
            if session is None:
                return
            session.status = terminal_status
            failure_detail = (detail or "Background draft generation did not complete successfully.").strip()
            if len(failure_detail) > 500:
                failure_detail = f"{failure_detail[:497]}..."
            db.add(
                ActionLogModel(
                    session_id=session_id,
                    event_type=failure_event_type,
                    title=title,
                    detail=failure_detail,
                    actor="system",
                )
            )
            db.commit()
            logger.error(
                "Failure stage persisted background generation error",
                extra={"event": log_event, "failure_detail": failure_detail},
            )

    @staticmethod
    def mark_screenshot_job_failed(db, session_id: str, detail: str | None = None) -> None:  # type: ignore[no-untyped-def]
        """Return session to review so the BA can retry screenshot generation."""
        FailureStage.mark_failed(
            db,
            session_id,
            detail,
            title="Screenshot generation failed",
            failure_event_type="screenshot_generation_failed",
            terminal_status="review",
            log_event="screenshot_generation.stage_failed",
        )
