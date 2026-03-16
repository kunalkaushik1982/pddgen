r"""
Purpose: Helper for recording meaningful draft-session activity events.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\action_log_service.py
"""

from sqlalchemy.orm import Session

from app.models.action_log import ActionLogModel


class ActionLogService:
    """Persist meaningful session events without logging low-value UI noise."""

    def record(
        self,
        db: Session,
        *,
        session_id: str,
        event_type: str,
        title: str,
        detail: str = "",
        actor: str = "system",
    ) -> ActionLogModel:
        """Stage one action log row on the current session transaction."""
        action_log = ActionLogModel(
            session_id=session_id,
            event_type=event_type,
            title=title,
            detail=detail,
            actor=actor,
        )
        db.add(action_log)
        return action_log
