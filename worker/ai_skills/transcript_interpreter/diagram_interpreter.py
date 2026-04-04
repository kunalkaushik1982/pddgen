from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from worker.ai_skills.transcript_interpreter.client import extract_content, parse_json_object
from worker.ai_skills.transcript_interpreter.diagrams import normalize_diagram_view
from worker.ai_skills.transcript_interpreter.diagram_prompts import DIAGRAM_INTERPRETATION_PROMPT
from worker.ai_skills.transcript_interpreter.models import DiagramInterpretation
from worker.ai_skills.transcript_interpreter.workflow_runtime import post_json


def interpret_diagrams(
    *,
    settings: Any,
    session_title: str,
    diagram_type: str,
    steps: Sequence[Mapping[str, Any]],
    notes: Sequence[Mapping[str, Any]],
) -> DiagramInterpretation | None:
    if diagram_type.lower() != "flowchart":
        return None

    step_payload = [
        {
            "step_number": step.get("step_number"),
            "application_name": step.get("application_name", ""),
            "action_text": step.get("action_text", ""),
            "source_data_note": step.get("source_data_note", ""),
            "supporting_transcript_text": step.get("supporting_transcript_text", ""),
        }
        for step in steps
    ]
    note_payload = [
        {
            "text": note.get("text", ""),
            "inference_type": note.get("inference_type", ""),
            "confidence": note.get("confidence", ""),
        }
        for note in notes
    ]

    payload = {
        "model": settings.ai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": DIAGRAM_INTERPRETATION_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "session_title": session_title,
                        "diagram_type": diagram_type,
                        "steps": step_payload,
                        "notes": note_payload,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }

    body = post_json(settings=settings, payload=payload, context="diagram interpretation")
    content = extract_content(body)
    parsed = parse_json_object(content)
    overview = normalize_diagram_view(parsed.get("overview", {}), "overview", session_title)
    detailed = normalize_diagram_view(parsed.get("detailed", {}), "detailed", session_title)
    return DiagramInterpretation(overview=overview, detailed=detailed)
