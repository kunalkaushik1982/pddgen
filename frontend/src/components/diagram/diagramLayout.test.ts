import { describe, expect, it } from "vitest";

import { buildFlowchartLayout } from "./diagramLayout";
import type { DiagramModel } from "../../types/diagram";

function buildLinearDetailedModel(stepCount: number): DiagramModel {
  return {
    diagramType: "flowchart",
    viewType: "detailed",
    title: "Linear process",
    nodes: Array.from({ length: stepCount }, (_, index) => ({
      id: `s${index + 1}`,
      label: `Step ${index + 1}`,
      category: "process" as const,
      stepRange: `Step ${index + 1}`,
    })),
    edges: Array.from({ length: Math.max(0, stepCount - 1) }, (_, index) => ({
      id: `e${index + 1}`,
      source: `s${index + 1}`,
      target: `s${index + 2}`,
      label: "",
    })),
  };
}

function buildBranchedDetailedModel(): DiagramModel {
  return {
    diagramType: "flowchart",
    viewType: "detailed",
    title: "Branched process",
    nodes: [
      { id: "s1", label: "Start step", category: "process", stepRange: "Step 1" },
      { id: "d1", label: "Decision", category: "decision", stepRange: "Step 2" },
      { id: "c1", label: "Yes path", category: "process", stepRange: "Step 3" },
      { id: "m1", label: "Merge", category: "process", stepRange: "Step 4" },
      { id: "r1", label: "No path", category: "process", stepRange: "Step 5" },
      { id: "s2", label: "Continue", category: "process", stepRange: "Step 6" },
    ],
    edges: [
      { id: "e1", source: "s1", target: "d1", label: "" },
      { id: "e2", source: "d1", target: "c1", label: "Yes" },
      { id: "e3", source: "d1", target: "r1", label: "No" },
      { id: "e4", source: "c1", target: "m1", label: "" },
      { id: "e5", source: "r1", target: "m1", label: "" },
      { id: "e6", source: "m1", target: "s2", label: "" },
    ],
  };
}

function getNodeBox(node: {
  position: { x: number; y: number };
  width?: number | null;
  height?: number | null;
  style?: { width?: number | string; minHeight?: number | string };
}) {
  const width = typeof node.width === "number" ? node.width : typeof node.style?.width === "number" ? node.style.width : 220;
  const height =
    typeof node.height === "number" ? node.height : typeof node.style?.minHeight === "number" ? node.style.minHeight : 84;
  return {
    left: node.position.x,
    right: node.position.x + width,
    top: node.position.y,
    bottom: node.position.y + height,
  };
}

function boxesOverlap(a: ReturnType<typeof getNodeBox>, b: ReturnType<typeof getNodeBox>): boolean {
  return !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top);
}

describe("buildFlowchartLayout", () => {
  it("uses width and avoids node overlap for long default detailed flows", async () => {
    const model = buildLinearDetailedModel(7);

    const layout = await buildFlowchartLayout(model);

    const xPositions = layout.nodes.map((node) => node.position.x);
    const yPositions = layout.nodes.map((node) => node.position.y);
    const widthSpan = Math.max(...xPositions) - Math.min(...xPositions);
    const heightSpan = Math.max(...yPositions) - Math.min(...yPositions);

    expect(widthSpan).toBeLessThan(260);
    expect(heightSpan).toBeGreaterThan(120);

    const boxes = layout.nodes.map(getNodeBox);
    for (let index = 0; index < boxes.length; index += 1) {
      for (let compareIndex = index + 1; compareIndex < boxes.length; compareIndex += 1) {
        expect(boxesOverlap(boxes[index], boxes[compareIndex])).toBe(false);
      }
    }
  });

  it("fans branches horizontally while keeping the overall flow top-down", async () => {
    const model = buildBranchedDetailedModel();

    const layout = await buildFlowchartLayout(model);

    const byId = new Map(layout.nodes.map((node) => [node.id, node]));
    const start = byId.get("s1");
    const decision = byId.get("d1");
    const yesPath = byId.get("c1");
    const noPath = byId.get("r1");
    const merge = byId.get("m1");
    const continueNode = byId.get("s2");

    expect(start).toBeTruthy();
    expect(decision).toBeTruthy();
    expect(yesPath).toBeTruthy();
    expect(noPath).toBeTruthy();
    expect(merge).toBeTruthy();
    expect(continueNode).toBeTruthy();

    expect(decision!.position.y).toBeGreaterThan(start!.position.y);
    expect(continueNode!.position.y).toBeGreaterThan(merge!.position.y);

    const branchWidth = Math.abs(yesPath!.position.x - noPath!.position.x);
    expect(branchWidth).toBeGreaterThan(200);
  });
});
