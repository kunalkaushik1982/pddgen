from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from worker.services.ai_transcript.client import extract_content, parse_json_object, post_chat_completion
from worker.services.ai_transcript.diagrams import normalize_diagram_view
from worker.services.ai_transcript.models import DiagramInterpretation


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
                "content": (
                    "You convert discovered process steps into two flowchart graph models for a PDD. "
                    "Return strict JSON with exactly two keys: overview and detailed. "
                    "Each view must contain title, nodes, and edges. "
                    "Each node must contain id, label, category, step_range. "
                    "Each edge must contain id, source, target, label. "
                    "Allowed node categories are only process and decision. "
                    "Use only the discovered process evidence provided. "
                    "Do not invent correction nodes, retry nodes, merge nodes, helper nodes, or error-handling paths unless they are explicitly supported by the evidence. "
                    "Every node in each view must belong to one connected workflow. "
                    "Do not create isolated nodes. "
                    "Do not create disconnected subgraphs. "
                    "Every edge must reference valid node ids in the same view. "
                    "The graph must read as a coherent workflow from first node to last node. "
                    "Use category=decision only when the evidence explicitly describes a conditional branch or multiple possible outcomes, such as if/else, yes/no, whether X exists, approved/rejected, or pass/fail. "
                    "Do not classify simple actions as decision. "
                    "Actions such as open, enter, type, select, choose, save, submit, click, navigate, validate, check, and verify must remain process nodes unless the evidence explicitly describes branching or alternate outcomes. "
                    "Overview is a compact business summary of the same process. "
                    "Overview should prefer 5 to 9 nodes when possible. "
                    "Overview should group detailed steps into business-level phases, stay mostly linear, and include a decision node only when it is a major business branch that materially changes the flow. "
                    "Do not include low-level technical validations in overview unless they are a major business branch. "
                    "Detailed must preserve discovered business action order. "
                    "Detailed should use one node per evidence-backed business action or explicit decision point. "
                    "If the evidence does not clearly support branching, keep the detailed graph linear. "
                    "Use concise, professional business labels. "
                    "Do not repeat raw transcript wording unnecessarily. "
                    "Do not use vague labels like Process Step or Do Action. "
                    "Every node must include a valid step_range using the provided step numbers, such as Step 3 or Steps 4-6. "
                    "Example linear case: Open SAP -> Enter vendor number -> Enter material details -> Save purchase order. All nodes must be process nodes in one connected linear graph. "
                    "Example decision case: Check whether supplier exists -> If supplier does not exist, create supplier -> Continue purchase order creation. A decision node is allowed only because branching is explicit. "
                    "Do not return markdown. Return only valid JSON."
                ),
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

    endpoint = f"{settings.ai_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.ai_api_key}", "Content-Type": "application/json"}
    body = post_chat_completion(
        timeout_seconds=settings.ai_timeout_seconds,
        endpoint=endpoint,
        headers=headers,
        payload=payload,
        context="diagram interpretation",
    )
    content = extract_content(body)
    parsed = parse_json_object(content)
    overview = normalize_diagram_view(parsed.get("overview", {}), "overview", session_title)
    detailed = normalize_diagram_view(parsed.get("detailed", {}), "detailed", session_title)
    return DiagramInterpretation(overview=overview, detailed=detailed)
