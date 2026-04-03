r"""
Purpose: Helper for recording meaningful draft-session activity events.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\action_log_service.py
"""

import json
from typing import Any, Protocol

from app.models.action_log import ActionLogModel


class _ActionLogSession(Protocol):
    def add(self, instance: Any) -> None: ...


class ActionLogService:
    """Persist meaningful session events without logging low-value UI noise."""

    def record(
        self,
        db: _ActionLogSession,
        *,
        session_id: str,
        event_type: str,
        title: str,
        detail: str = "",
        metadata: dict[str, Any] | None = None,
        actor: str = "system",
    ) -> ActionLogModel:
        """Stage one action log row on the current session transaction."""
        action_log = ActionLogModel(
            session_id=session_id,
            event_type=event_type,
            title=title,
            detail=detail,
            metadata_json=json.dumps(metadata) if metadata else "",
            actor=actor,
        )
        db.add(action_log)
        return action_log
