# Diagram Quality Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve generated session diagrams so they produce fewer fake decision nodes, cleaner business-level graphs, better default layouts, and more useful editing controls.

**Architecture:** Keep the current React Flow + backend JSON architecture, but strengthen the diagram generation pipeline with deterministic post-processing between AI output and persisted diagram JSON. Treat the frontend layout engine as a renderer/layout layer, not the source of graph quality. After graph normalization and simplification, tune ELK per view type and add a small set of editor controls to correct node semantics without needing regeneration.

**Tech Stack:** Python worker AI skill pipeline, FastAPI backend, React + TypeScript frontend, React Flow, ELKjs, unittest/Vitest/TypeScript checks

---

## File Map

### Existing files to modify

- `worker/ai_skills/diagram_generation/skill.py`
  Diagram AI output normalization for the worker path.
- `worker/ai_skills/transcript_interpreter/diagrams.py`
  Shared transcript-interpreter diagram normalization path; must stay behaviorally aligned with `diagram_generation/skill.py`.
- `worker/tests/test_diagram_generation_skill.py`
  Regression coverage for fake decisions, real decisions, and later simplification behavior.
- `frontend/src/components/diagram/diagramLayout.ts`
  ELK layout configuration and per-view layout behavior.
- `frontend/src/components/diagram/diagramLayout.test.ts`
  Frontend regression coverage for layout behavior.
- `frontend/src/components/diagram/FlowchartPreviewPanel.tsx`
  Editor UX enhancements such as node-type conversion or “re-layout” actions.
- `frontend/src/types/diagram.ts`
  Frontend diagram model typing, if editor controls need extra action state or metadata.
- `docs/2026-04-17-codebase-scan-conversation.md`
  Append summary of implemented diagram-quality changes after work is done.

### New files to create

- `worker/ai_skills/diagram_generation/postprocess.py`
  Focused deterministic graph cleanup helpers: branch validation, decision downgrades, linear-step collapsing, label cleanup.
- `worker/tests/test_diagram_generation_postprocess.py`
  Unit tests for deterministic post-processing independent of the AI skill wrapper.
- `frontend/src/components/diagram/diagramActions.ts`
  Small pure helpers for editor-side graph actions such as converting node type or simplifying selected nodes.
- `frontend/src/components/diagram/diagramActions.test.ts`
  Frontend tests for the pure graph action helpers.

## Scope Notes

This plan is intentionally split into three phases:

1. model normalization
2. deterministic simplification
3. editor and layout polish

Each phase should leave the product in a releasable state.

---

### Task 1: Extract deterministic diagram post-processing

**Files:**
- Create: `worker/ai_skills/diagram_generation/postprocess.py`
- Modify: `worker/ai_skills/diagram_generation/skill.py`
- Modify: `worker/ai_skills/transcript_interpreter/diagrams.py`
- Test: `worker/tests/test_diagram_generation_postprocess.py`

- [ ] **Step 1: Write the failing tests for decision validation**

Create `worker/tests/test_diagram_generation_postprocess.py` with:

```python
from __future__ import annotations

import unittest

from worker.ai_skills.diagram_generation.postprocess import normalize_and_cleanup_diagram_view


class DiagramPostprocessTests(unittest.TestCase):
    def test_downgrades_linear_decision_to_process(self) -> None:
        view = {
            "title": "Vendor creation",
            "nodes": [
                {"id": "n1", "label": "Open transaction", "category": "process", "step_range": "Step 1"},
                {"id": "n2", "label": "Create vendor by entering code", "category": "decision", "step_range": "Step 2"},
                {"id": "n3", "label": "Enter vendor details", "category": "process", "step_range": "Step 3"},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "label": ""},
                {"id": "e2", "source": "n2", "target": "n3", "label": ""},
            ],
        }

        normalized = normalize_and_cleanup_diagram_view(view, "detailed", "Vendor creation")
        by_id = {node["id"]: node for node in normalized["nodes"]}
        self.assertEqual(by_id["n2"]["category"], "process")

    def test_keeps_real_branching_decision(self) -> None:
        view = {
            "title": "Vendor creation",
            "nodes": [
                {"id": "n1", "label": "Check whether vendor exists", "category": "decision", "step_range": "Step 1"},
                {"id": "n2", "label": "Create vendor", "category": "process", "step_range": "Step 2"},
                {"id": "n3", "label": "Continue flow", "category": "process", "step_range": "Step 3"},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "label": "No"},
                {"id": "e2", "source": "n1", "target": "n3", "label": "Yes"},
            ],
        }

        normalized = normalize_and_cleanup_diagram_view(view, "detailed", "Vendor creation")
        by_id = {node["id"]: node for node in normalized["nodes"]}
        self.assertEqual(by_id["n1"]["category"], "decision")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the worker postprocess tests and verify they fail**

Run:

```powershell
python -m unittest worker.tests.test_diagram_generation_postprocess
```

Expected:

- fail because `worker.ai_skills.diagram_generation.postprocess` does not exist yet

- [ ] **Step 3: Write the minimal deterministic postprocess module**

Create `worker/ai_skills/diagram_generation/postprocess.py` with:

```python
from __future__ import annotations

from typing import Any


def _normalize_edge_label(value: object) -> str:
    return str(value or "").strip().lower()


def _normalize_structure(view: dict[str, object], view_type: str, session_title: str) -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    raw_nodes = view.get("nodes", []) if isinstance(view, dict) else []
    raw_edges = view.get("edges", []) if isinstance(view, dict) else []

    nodes: list[dict[str, str]] = []
    node_ids: set[str] = set()
    for index, item in enumerate(raw_nodes if isinstance(raw_nodes, list) else [], start=1):
        if not isinstance(item, dict):
            continue
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
    for index, item in enumerate(raw_edges if isinstance(raw_edges, list) else [], start=1):
        if not isinstance(item, dict):
            continue
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

    title = str(view.get("title", "") or session_title).strip() or session_title
    return nodes, edges, title


def _is_real_decision(node_id: str, outgoing_edges: list[dict[str, str]]) -> bool:
    if len(outgoing_edges) < 2:
        return False
    distinct_targets = {edge["target"] for edge in outgoing_edges if edge.get("target")}
    if len(distinct_targets) < 2:
        return False
    labels = {_normalize_edge_label(edge.get("label", "")) for edge in outgoing_edges}
    if {"yes", "no"} <= labels:
        return True
    return True


def normalize_and_cleanup_diagram_view(view: dict[str, Any], view_type: str, session_title: str) -> dict[str, Any]:
    nodes, edges, title = _normalize_structure(view, view_type, session_title)

    outgoing_edges_by_source: dict[str, list[dict[str, str]]] = {}
    for edge in edges:
        outgoing_edges_by_source.setdefault(edge["source"], []).append(edge)

    for node in nodes:
        if node["category"] != "decision":
            continue
        if not _is_real_decision(node["id"], outgoing_edges_by_source.get(node["id"], [])):
            node["category"] = "process"

    if not nodes:
        nodes = [{"id": f"{view_type}_n1", "label": "No process steps available", "category": "process", "step_range": ""}]
        edges = []

    return {
        "diagram_type": "flowchart",
        "view_type": view_type,
        "title": title,
        "nodes": nodes,
        "edges": edges,
    }
```

- [ ] **Step 4: Wire both normalization paths to the shared helper**

Modify `worker/ai_skills/diagram_generation/skill.py` so it imports and uses:

```python
from worker.ai_skills.diagram_generation.postprocess import normalize_and_cleanup_diagram_view
```

and replace:

```python
overview=normalize_diagram_view(parsed.get("overview", {}), "overview", input.session_title),
detailed=normalize_diagram_view(parsed.get("detailed", {}), "detailed", input.session_title),
```

with:

```python
overview=normalize_and_cleanup_diagram_view(parsed.get("overview", {}), "overview", input.session_title),
detailed=normalize_and_cleanup_diagram_view(parsed.get("detailed", {}), "detailed", input.session_title),
```

Modify `worker/ai_skills/transcript_interpreter/diagrams.py` to become a thin wrapper:

```python
from __future__ import annotations

from typing import Any

from worker.ai_skills.diagram_generation.postprocess import normalize_and_cleanup_diagram_view


def normalize_diagram_view(view: dict[str, Any], view_type: str, session_title: str) -> dict[str, Any]:
    return normalize_and_cleanup_diagram_view(view, view_type, session_title)
```

- [ ] **Step 5: Run the postprocess tests and existing worker diagram tests**

Run:

```powershell
python -m unittest worker.tests.test_diagram_generation_postprocess
python -m unittest worker.tests.test_diagram_generation_skill
python -m compileall worker
```

Expected:

- all tests pass
- compileall succeeds

- [ ] **Step 6: Commit**

```bash
git add worker/ai_skills/diagram_generation/postprocess.py worker/ai_skills/diagram_generation/skill.py worker/ai_skills/transcript_interpreter/diagrams.py worker/tests/test_diagram_generation_postprocess.py worker/tests/test_diagram_generation_skill.py
git commit -m "Improve diagram decision normalization"
```

---

### Task 2: Add deterministic simplification for noisy linear chains

**Files:**
- Modify: `worker/ai_skills/diagram_generation/postprocess.py`
- Modify: `worker/tests/test_diagram_generation_postprocess.py`

- [ ] **Step 1: Write the failing simplification test**

Add to `worker/tests/test_diagram_generation_postprocess.py`:

```python
    def test_collapses_long_linear_micro_steps_into_fewer_business_nodes(self) -> None:
        view = {
            "title": "Vendor creation",
            "nodes": [
                {"id": "n1", "label": "Navigate to logistics", "category": "process", "step_range": "Step 1"},
                {"id": "n2", "label": "Open vendor master", "category": "process", "step_range": "Step 2"},
                {"id": "n3", "label": "Enter account group", "category": "process", "step_range": "Step 3"},
                {"id": "n4", "label": "Enter vendor details", "category": "process", "step_range": "Step 4"},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "label": ""},
                {"id": "e2", "source": "n2", "target": "n3", "label": ""},
                {"id": "e3", "source": "n3", "target": "n4", "label": ""},
            ],
        }

        normalized = normalize_and_cleanup_diagram_view(view, "detailed", "Vendor creation")
        self.assertLessEqual(len(normalized["nodes"]), 3)
```

- [ ] **Step 2: Run the postprocess tests and verify this new one fails**

Run:

```powershell
python -m unittest worker.tests.test_diagram_generation_postprocess
```

Expected:

- new test fails because simplification is not implemented yet

- [ ] **Step 3: Add minimal linear-chain simplification**

Extend `worker/ai_skills/diagram_generation/postprocess.py` with:

```python
def _is_linear_chain(nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> bool:
    incoming: dict[str, int] = {node["id"]: 0 for node in nodes}
    outgoing: dict[str, int] = {node["id"]: 0 for node in nodes}
    for edge in edges:
        outgoing[edge["source"]] = outgoing.get(edge["source"], 0) + 1
        incoming[edge["target"]] = incoming.get(edge["target"], 0) + 1
    branching_nodes = sum(1 for node in nodes if outgoing.get(node["id"], 0) > 1 or incoming.get(node["id"], 0) > 1)
    return branching_nodes == 0


def _collapse_linear_groups(nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if len(nodes) <= 3 or not _is_linear_chain(nodes, edges):
        return nodes, edges

    grouped: list[list[dict[str, str]]] = [nodes[0:2], nodes[2:]]
    collapsed_nodes: list[dict[str, str]] = []
    for index, group in enumerate(grouped, start=1):
        labels = [item["label"] for item in group if item["label"]]
        step_ranges = [item["step_range"] for item in group if item["step_range"]]
        collapsed_nodes.append(
            {
                "id": f"group_{index}",
                "label": labels[-1] if labels else f"Step group {index}",
                "category": "process",
                "step_range": " / ".join(step_ranges[:2]),
            }
        )

    collapsed_edges = []
    for index in range(1, len(collapsed_nodes)):
        collapsed_edges.append(
            {
                "id": f"group_edge_{index}",
                "source": collapsed_nodes[index - 1]["id"],
                "target": collapsed_nodes[index]["id"],
                "label": "",
            }
        )
    return collapsed_nodes, collapsed_edges
```

Then, inside `normalize_and_cleanup_diagram_view(...)`, after decision cleanup:

```python
    if view_type == "detailed":
        nodes, edges = _collapse_linear_groups(nodes, edges)
```

- [ ] **Step 4: Run the postprocess tests again**

Run:

```powershell
python -m unittest worker.tests.test_diagram_generation_postprocess
```

Expected:

- all tests pass

- [ ] **Step 5: Commit**

```bash
git add worker/ai_skills/diagram_generation/postprocess.py worker/tests/test_diagram_generation_postprocess.py
git commit -m "Simplify noisy linear diagram chains"
```

---

### Task 3: Tune ELK layout separately for detailed and overview views

**Files:**
- Modify: `frontend/src/components/diagram/diagramLayout.ts`
- Modify: `frontend/src/components/diagram/diagramLayout.test.ts`

- [ ] **Step 1: Write the failing overview-layout test**

Add to `frontend/src/components/diagram/diagramLayout.test.ts`:

```typescript
  it("keeps overview diagrams compact while detailed diagrams stay top-down", async () => {
    const overviewModel: DiagramModel = {
      diagramType: "flowchart",
      viewType: "overview",
      title: "Overview",
      nodes: [
        { id: "n1", label: "Start", category: "process", stepRange: "Steps 1-2" },
        { id: "n2", label: "Review", category: "process", stepRange: "Steps 3-4" },
        { id: "n3", label: "Save", category: "process", stepRange: "Steps 5-6" },
      ],
      edges: [
        { id: "e1", source: "n1", target: "n2", label: "" },
        { id: "e2", source: "n2", target: "n3", label: "" },
      ],
    };

    const layout = await buildFlowchartLayout(overviewModel);
    const xPositions = layout.nodes.map((node) => node.position.x);
    expect(Math.max(...xPositions) - Math.min(...xPositions)).toBeGreaterThan(150);
  });
```

- [ ] **Step 2: Run the focused frontend test file and verify current behavior**

Run:

```powershell
npm run test -- src/components/diagram/diagramLayout.test.ts
```

Expected:

- either fail on the new assertion or reveal existing overview behavior is still too static

- [ ] **Step 3: Refactor layout options into explicit per-view configuration**

In `frontend/src/components/diagram/diagramLayout.ts`, introduce:

```typescript
type ElkLayoutMode = "overview" | "detailed";

function getElkLayoutOptions(mode: ElkLayoutMode): Record<string, string> {
  if (mode === "overview") {
    return {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.spacing.nodeNode": "90",
      "elk.layered.spacing.nodeNodeBetweenLayers": "130",
      "elk.spacing.edgeNode": "40",
      "elk.edgeRouting": "ORTHOGONAL",
    };
  }

  return {
    "elk.algorithm": "layered",
    "elk.direction": "DOWN",
    "elk.spacing.nodeNode": "100",
    "elk.layered.spacing.nodeNodeBetweenLayers": "140",
    "elk.spacing.edgeNode": "48",
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
    "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
    "elk.contentAlignment": "[H_CENTER, V_TOP]",
  };
}
```

Use `getElkLayoutOptions("detailed")` inside the detailed layout builder. For overview, replace the purely manual row placement with an ELK pass or keep the manual grid only if the new test already passes and visual review confirms it is good enough.

- [ ] **Step 4: Run frontend verification**

Run:

```powershell
npm run test -- src/components/diagram/diagramLayout.test.ts
npm exec tsc -- --noEmit
```

Expected:

- tests pass
- typecheck passes

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/diagram/diagramLayout.ts frontend/src/components/diagram/diagramLayout.test.ts
git commit -m "Tune ELK layout by diagram view"
```

---

### Task 4: Add editor-side node type conversion

**Files:**
- Create: `frontend/src/components/diagram/diagramActions.ts`
- Create: `frontend/src/components/diagram/diagramActions.test.ts`
- Modify: `frontend/src/components/diagram/FlowchartPreviewPanel.tsx`

- [ ] **Step 1: Write the failing graph-action test**

Create `frontend/src/components/diagram/diagramActions.test.ts` with:

```typescript
import { describe, expect, it } from "vitest";
import type { Node } from "reactflow";
import { convertNodeCategory } from "./diagramActions";

describe("convertNodeCategory", () => {
  it("updates node type and category data", () => {
    const nodes = [
      {
        id: "n1",
        type: "decision",
        position: { x: 0, y: 0 },
        data: { label: "Check vendor", category: "decision", stepRange: "Step 1", viewType: "detailed" },
      } as Node,
    ];

    const nextNodes = convertNodeCategory(nodes, "n1", "process");
    expect(nextNodes[0].type).toBe("process");
    expect(String((nextNodes[0].data as { category: string }).category)).toBe("process");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
npm run test -- src/components/diagram/diagramActions.test.ts
```

Expected:

- fail because `diagramActions.ts` does not exist

- [ ] **Step 3: Implement the pure helper**

Create `frontend/src/components/diagram/diagramActions.ts` with:

```typescript
import type { Node } from "reactflow";

export function convertNodeCategory(nodes: Node[], nodeId: string, category: "process" | "decision"): Node[] {
  return nodes.map((node) =>
    node.id === nodeId
      ? {
          ...node,
          type: category,
          data: {
            ...(typeof node.data === "object" && node.data ? node.data : {}),
            category,
          },
        }
      : node,
  );
}
```

- [ ] **Step 4: Add a minimal inspector action**

In `frontend/src/components/diagram/FlowchartPreviewPanel.tsx`:

- import `convertNodeCategory`
- when a node is selected, show:

```tsx
<button
  type="button"
  className="button-secondary"
  onClick={() => {
    rememberForUndo();
    setNodes((currentNodes) => attachNodeEditing(convertNodeCategory(currentNodes, selectedNode.id, "process")));
  }}
  disabled={isSavingLayout}
>
  Convert to process
</button>
```

and:

```tsx
<button
  type="button"
  className="button-secondary"
  onClick={() => {
    rememberForUndo();
    setNodes((currentNodes) => attachNodeEditing(convertNodeCategory(currentNodes, selectedNode.id, "decision")));
  }}
  disabled={isSavingLayout}
>
  Convert to decision
</button>
```

- [ ] **Step 5: Run frontend verification**

Run:

```powershell
npm run test -- src/components/diagram/diagramActions.test.ts
npm exec tsc -- --noEmit
```

Expected:

- test passes
- typecheck passes

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/diagram/diagramActions.ts frontend/src/components/diagram/diagramActions.test.ts frontend/src/components/diagram/FlowchartPreviewPanel.tsx
git commit -m "Add diagram node type conversion controls"
```

---

### Task 5: Document the new diagram behavior

**Files:**
- Modify: `docs/2026-04-17-codebase-scan-conversation.md`

- [ ] **Step 1: Update the conversation log with implemented changes**

Append short sections describing:

- fake decision node downgrade
- deterministic linear-chain simplification
- ELK per-view tuning
- editor-side node type conversion

- [ ] **Step 2: Verify docs render cleanly**

Run:

```powershell
Get-Content docs\2026-04-17-codebase-scan-conversation.md
```

Expected:

- updated markdown reads clearly

- [ ] **Step 3: Commit**

```bash
git add docs/2026-04-17-codebase-scan-conversation.md
git commit -m "Document diagram quality improvements"
```

---

## Self-Review

### Spec coverage

Covered:

- model quality improvement through deterministic cleanup
- fake decision removal
- simplification of noisy linear detailed graphs
- ELK tuning for better default layouts
- editor-side correction path for node semantics

Remaining intentionally out of scope for this plan:

- full BPMN migration
- new backend inspection/debug endpoint
- large export pipeline redesign away from PNG artifacts

### Placeholder scan

Checked:

- no `TODO`/`TBD`
- each task has explicit file targets
- each task includes concrete commands

### Type consistency

Checked:

- uses existing `DiagramModel`, `Node`, and React Flow conventions
- worker normalization stays centralized through a new shared postprocess module

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-18-diagram-quality-improvements.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
