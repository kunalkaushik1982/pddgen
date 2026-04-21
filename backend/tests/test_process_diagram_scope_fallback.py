"""Regression: scoped diagram read falls back to session-level JSON when group payload is empty."""

from __future__ import annotations

import json

from app.services.generation.process_diagram_service import ProcessDiagramService


class _FakeGroup:
    def __init__(self, group_id: str) -> None:
        self.id = group_id
        self.title = "G1"
        self.overview_diagram_json = ""
        self.detailed_diagram_json = ""


class _FakeSession:
    def __init__(self) -> None:
        self.id = "sess-1"
        self.title = "S"
        self.diagram_type = "flowchart"
        empty = {
            "diagram_type": "flowchart",
            "view_type": "detailed",
            "title": "S",
            "nodes": [],
            "edges": [],
        }
        payload = json.dumps(empty)
        self.overview_diagram_json = payload
        self.detailed_diagram_json = payload
        self.process_groups = [_FakeGroup("g1")]
        self.process_steps = []
        self.process_notes = []
        self.diagram_layouts = []


def test_build_diagram_model_uses_session_json_when_group_diagram_empty() -> None:
    svc = ProcessDiagramService()
    session = _FakeSession()
    model = svc.build_diagram_model(session, "detailed", process_group_id="g1")
    assert model["nodes"] == []
    assert model["edges"] == []
