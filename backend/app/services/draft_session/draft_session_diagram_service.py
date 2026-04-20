r"""
Purpose: Diagram and layout mutations for draft sessions.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\draft_session_diagram_service.py
"""

import json
from typing import Literal

from sqlalchemy.orm import Session

from app.models.diagram_layout import DiagramLayoutModel
from app.services.platform.action_log_service import ActionLogService


class DraftSessionDiagramService:
    """Encapsulate draft-session diagram reads and writes."""

    def __init__(self, *, action_log_service: ActionLogService) -> None:
        self.action_log_service = action_log_service

    def save_diagram_model(
        self,
        db: Session,
        *,
        session,
        payload,
        view: Literal["overview", "detailed"],
        process_group_id: str | None = None,
    ) -> dict:  # type: ignore[no-untyped-def]
        model_payload = {
            "diagram_type": "flowchart",
            "view_type": view,
            "title": payload.title,
            "nodes": [node.model_dump() for node in payload.nodes],
            "edges": [edge.model_dump() for edge in payload.edges],
        }
        target = session
        if process_group_id:
            target = next((group for group in getattr(session, "process_groups", []) if group.id == process_group_id), session)
        if view == "detailed":
            target.detailed_diagram_json = json.dumps(model_payload)
        else:
            target.overview_diagram_json = json.dumps(model_payload)
        db.add(target)
        db.commit()
        db.refresh(target)
        return model_payload

    def get_diagram_layout(
        self,
        db: Session,
        *,
        session_id: str,
        view: Literal["overview", "detailed"],
        process_group_id: str | None = None,
    ) -> dict:
        layout = (
            db.query(DiagramLayoutModel)
            .filter(
                DiagramLayoutModel.session_id == session_id,
                DiagramLayoutModel.view_type == view,
                DiagramLayoutModel.process_group_id == process_group_id,
            )
            .one_or_none()
        )
        nodes: list[dict] = []
        export_preset = "balanced"
        canvas_settings = {"theme": "dark", "show_grid": True, "grid_density": "medium"}
        if layout is not None and layout.layout_json:
            try:
                parsed = json.loads(layout.layout_json)
                if isinstance(parsed, dict):
                    nodes = parsed.get("nodes", [])
                    export_preset = parsed.get("export_preset", "balanced") or "balanced"
                    parsed_canvas_settings = parsed.get("canvas_settings", {})
                    if isinstance(parsed_canvas_settings, dict):
                        canvas_settings = {
                            "theme": parsed_canvas_settings.get("theme", "dark") or "dark",
                            "show_grid": bool(parsed_canvas_settings.get("show_grid", True)),
                            "grid_density": parsed_canvas_settings.get("grid_density", "medium") or "medium",
                        }
                elif isinstance(parsed, list):
                    nodes = parsed
            except json.JSONDecodeError:
                nodes = []
        return {
            "session_id": session_id,
            "process_group_id": process_group_id,
            "view_type": view,
            "nodes": nodes,
            "export_preset": export_preset,
            "canvas_settings": canvas_settings,
        }

    def save_diagram_layout(
        self,
        db: Session,
        *,
        session_id: str,
        payload,
        actor: str,
        view: Literal["overview", "detailed"],
        process_group_id: str | None = None,
    ) -> dict:  # type: ignore[no-untyped-def]
        layout = (
            db.query(DiagramLayoutModel)
            .filter(
                DiagramLayoutModel.session_id == session_id,
                DiagramLayoutModel.view_type == view,
                DiagramLayoutModel.process_group_id == process_group_id,
            )
            .one_or_none()
        )
        if layout is None:
            layout = DiagramLayoutModel(session_id=session_id, process_group_id=process_group_id, view_type=view)
            db.add(layout)

        previous_canvas_settings = {"theme": "dark", "show_grid": True, "grid_density": "medium"}
        if layout.layout_json:
            try:
                previous_payload = json.loads(layout.layout_json)
                if isinstance(previous_payload, dict):
                    parsed_previous_canvas = previous_payload.get("canvas_settings", {})
                    if isinstance(parsed_previous_canvas, dict):
                        previous_canvas_settings = {
                            "theme": parsed_previous_canvas.get("theme", "dark") or "dark",
                            "show_grid": bool(parsed_previous_canvas.get("show_grid", True)),
                            "grid_density": parsed_previous_canvas.get("grid_density", "medium") or "medium",
                        }
            except json.JSONDecodeError:
                previous_canvas_settings = {"theme": "dark", "show_grid": True, "grid_density": "medium"}

        next_canvas_settings = payload.canvas_settings.model_dump()
        layout.layout_json = json.dumps(
            {
                "nodes": [node.model_dump() for node in payload.nodes],
                "export_preset": payload.export_preset,
                "canvas_settings": next_canvas_settings,
            }
        )
        theme_changed = previous_canvas_settings.get("theme") != next_canvas_settings.get("theme")
        grid_changed = previous_canvas_settings.get("show_grid") != next_canvas_settings.get("show_grid")
        if theme_changed or grid_changed:
            appearance_parts: list[str] = []
            if theme_changed:
                appearance_parts.append(f"theme {next_canvas_settings.get('theme', 'dark')}")
            if grid_changed:
                appearance_parts.append(f"grid {'on' if next_canvas_settings.get('show_grid', True) else 'off'}")
            action_title = "Diagram appearance updated"
            action_detail = f"{view.capitalize()} diagram saved with " + ", ".join(appearance_parts) + "."
        else:
            action_title = "Diagram saved"
            action_detail = f"{view.capitalize()} layout saved with {len(payload.nodes)} positioned nodes."
        self.action_log_service.record(
            db,
            session_id=session_id,
            event_type="diagram_saved",
            title=action_title,
            detail=action_detail,
            actor=actor,
        )
        db.commit()
        db.refresh(layout)
        parsed = json.loads(layout.layout_json) if layout.layout_json else {"nodes": [], "export_preset": "balanced"}
        return {
            "session_id": session_id,
            "process_group_id": process_group_id,
            "view_type": view,
            "nodes": parsed.get("nodes", []),
            "export_preset": parsed.get("export_preset", "balanced") or "balanced",
            "canvas_settings": parsed.get("canvas_settings", {"theme": "dark", "show_grid": True, "grid_density": "medium"}),
        }
