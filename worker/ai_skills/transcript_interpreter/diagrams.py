from __future__ import annotations

from typing import Any


def normalize_diagram_view(view: dict[str, Any], view_type: str, session_title: str) -> dict[str, Any]:
    raw_nodes = view.get("nodes", []) if isinstance(view, dict) else []
    raw_edges = view.get("edges", []) if isinstance(view, dict) else []

    nodes: list[dict[str, str]] = []
    node_ids: set[str] = set()
    for index, item in enumerate(raw_nodes, start=1):
        node_id = str(item.get("id", "") or f"{view_type}_n{index}").strip()
        if not node_id or node_id in node_ids:
            node_id = f"{view_type}_n{index}"
        node_ids.add(node_id)
        category = str(item.get("category", "process") or "process").strip().lower()
        if category not in {"process", "decision"}:
            category = "process"
        nodes.append(
            {
                "id": node_id,
                "label": str(item.get("label", "") or "").strip() or f"Step {index}",
                "category": category,
                "step_range": str(item.get("step_range", "") or "").strip(),
            }
        )

    edges: list[dict[str, str]] = []
    for index, item in enumerate(raw_edges, start=1):
        source = str(item.get("source", "") or "").strip()
        target = str(item.get("target", "") or "").strip()
        if source not in node_ids or target not in node_ids:
            continue
        edges.append(
            {
                "id": str(item.get("id", "") or f"{view_type}_e{index}").strip() or f"{view_type}_e{index}",
                "source": source,
                "target": target,
                "label": str(item.get("label", "") or "").strip(),
            }
        )

    if not nodes:
        nodes = [{"id": f"{view_type}_n1", "label": "No process steps available", "category": "process", "step_range": ""}]
        edges = []

    return {
        "diagram_type": "flowchart",
        "view_type": view_type,
        "title": str(view.get("title", "") or session_title).strip() or session_title,
        "nodes": nodes,
        "edges": edges,
    }
