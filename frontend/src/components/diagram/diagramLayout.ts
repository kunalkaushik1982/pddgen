/**
 * Purpose: Layout helpers for overview and detailed flowchart previews.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\diagram\diagramLayout.ts
 */

import { MarkerType, Position, type Edge, type Node } from "reactflow";

import type { DiagramLayoutNodePosition, DiagramModel } from "../../types/diagram";

const NODE_WIDTH = 220;
const NODE_HEIGHT = 84;
const NODE_MIN_LINES = 3;
const GRID_SIZE = 20;
const COLUMN_GAP = 52;
const ROW_GAP = 120;
const NODES_PER_ROW = 4;
const HANDLE_SLOTS = 4;

function estimateNodeMinHeight(label: string, category: string): number {
  if (category === "decision") {
    return 160;
  }
  const normalized = label.replace(/\n/g, " ");
  const approxCharsPerLine = 22;
  const lineCount = Math.max(NODE_MIN_LINES, Math.ceil(normalized.length / approxCharsPerLine));
  return Math.max(NODE_HEIGHT, 32 + lineCount * 22);
}

function getNodeWidth(node: DiagramModel["nodes"][number]): number {
  if (typeof node.width === "number" && Number.isFinite(node.width)) {
    return node.width;
  }
  return node.category === "decision" ? 160 : NODE_WIDTH;
}

function getNodeHeight(node: DiagramModel["nodes"][number], label: string, category: string): number {
  if (typeof node.height === "number" && Number.isFinite(node.height)) {
    return node.height;
  }
  return estimateNodeMinHeight(label, category);
}

function snapToGrid(value: number): number {
  return Math.round(value / GRID_SIZE) * GRID_SIZE;
}

export function snapNodePositions(nodes: Node[]): Node[] {
  return nodes.map((node) => ({
    ...node,
    position: {
      x: snapToGrid(node.position.x),
      y: snapToGrid(node.position.y),
    },
  }));
}

function getRowIndex(index: number): number {
  return Math.floor(index / NODES_PER_ROW);
}

function getIsReverseRow(rowIndex: number): boolean {
  return rowIndex % 2 === 1;
}

function buildOverviewNodes(model: DiagramModel): Node[] {
  return model.nodes.map((node, zeroBasedIndex) => {
    const rowIndex = getRowIndex(zeroBasedIndex);
    const columnIndex = zeroBasedIndex % NODES_PER_ROW;
    const isReverseRow = getIsReverseRow(rowIndex);
    const visualColumnIndex = isReverseRow ? NODES_PER_ROW - 1 - columnIndex : columnIndex;

    return {
      id: node.id,
      type: zeroBasedIndex === 0 ? "start" : node.category,
      position: {
        x: visualColumnIndex * (NODE_WIDTH + COLUMN_GAP),
        y: rowIndex * ROW_GAP,
      },
      data: {
        label: zeroBasedIndex === 0 ? `Start\n${node.label}` : node.label,
        stepRange: node.stepRange,
        category: zeroBasedIndex === 0 ? "start" : node.category,
        viewType: model.viewType,
      },
      style: {
        width: getNodeWidth(node),
        minHeight: getNodeHeight(node, zeroBasedIndex === 0 ? `Start\n${node.label}` : node.label, zeroBasedIndex === 0 ? "start" : node.category),
      },
    };
  });
}

function getOverviewHandles(sourceNode: Node, targetNode: Node): { sourceHandle: string; targetHandle: string } {
  const sourceCenterX = sourceNode.position.x + NODE_WIDTH / 2;
  const sourceCenterY = sourceNode.position.y + NODE_HEIGHT / 2;
  const targetCenterX = targetNode.position.x + NODE_WIDTH / 2;
  const targetCenterY = targetNode.position.y + NODE_HEIGHT / 2;
  const dx = targetCenterX - sourceCenterX;
  const dy = targetCenterY - sourceCenterY;

  if (Math.abs(dx) >= Math.abs(dy)) {
    return dx >= 0
      ? { sourceHandle: "right", targetHandle: "left" }
      : { sourceHandle: "left", targetHandle: "right" };
  }

  return dy >= 0
    ? { sourceHandle: "bottom", targetHandle: "top" }
    : { sourceHandle: "top", targetHandle: "bottom" };
}

function getRenderedNodeWidth(node: Node): number {
  if (typeof node.width === "number" && Number.isFinite(node.width)) {
    return node.width;
  }
  return typeof node.style?.width === "number" ? node.style.width : NODE_WIDTH;
}

function getRenderedNodeHeight(node: Node): number {
  if (typeof node.height === "number" && Number.isFinite(node.height)) {
    return node.height;
  }
  return typeof node.style?.minHeight === "number" ? node.style.minHeight : NODE_HEIGHT;
}

function getRelativeHandles(sourceNode: Node, targetNode: Node): { sourceSide: string; targetSide: string } {
  const sourceCenterX = sourceNode.position.x + getRenderedNodeWidth(sourceNode) / 2;
  const sourceCenterY = sourceNode.position.y + getRenderedNodeHeight(sourceNode) / 2;
  const targetCenterX = targetNode.position.x + getRenderedNodeWidth(targetNode) / 2;
  const targetCenterY = targetNode.position.y + getRenderedNodeHeight(targetNode) / 2;
  const dx = targetCenterX - sourceCenterX;
  const dy = targetCenterY - sourceCenterY;

  if (Math.abs(dx) >= Math.abs(dy)) {
    return dx >= 0 ? { sourceSide: "right", targetSide: "left" } : { sourceSide: "left", targetSide: "right" };
  }

  return dy >= 0 ? { sourceSide: "bottom", targetSide: "top" } : { sourceSide: "top", targetSide: "bottom" };
}

export function withAutoConnectionHandles(nextNodes: Node[], nextEdges: Edge[]): Edge[] {
  const nodeMap = new Map(nextNodes.map((node) => [node.id, node]));
  const sourceCounts = new Map<string, number>();
  const targetCounts = new Map<string, number>();

  return nextEdges.map((edge) => {
    if (edge.sourceHandle && edge.targetHandle) {
      return edge;
    }
    const sourceNode = nodeMap.get(edge.source);
    const targetNode = nodeMap.get(edge.target);
    if (!sourceNode || !targetNode) {
      return edge;
    }
    const { sourceSide, targetSide } = getRelativeHandles(sourceNode, targetNode);
    const sourceKey = `${edge.source}:${sourceSide}`;
    const targetKey = `${edge.target}:${targetSide}`;
    const sourceIndex = (sourceCounts.get(sourceKey) ?? 0) % HANDLE_SLOTS;
    const targetIndex = (targetCounts.get(targetKey) ?? 0) % HANDLE_SLOTS;
    sourceCounts.set(sourceKey, sourceIndex + 1);
    targetCounts.set(targetKey, targetIndex + 1);

    return {
      ...edge,
      sourceHandle: edge.sourceHandle ?? `source-${sourceSide}-${sourceIndex + 1}`,
      targetHandle: edge.targetHandle ?? `target-${targetSide}-${targetIndex + 1}`,
    };
  });
}

export function buildOverviewEdges(model: DiagramModel, nodes: Node[]): Edge[] {
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  return model.edges.map((edge) => ({
    ...getOverviewHandles(nodeMap.get(edge.source) ?? nodes[0], nodeMap.get(edge.target) ?? nodes[0]),
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label,
    type: "overview",
    animated: false,
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 18,
      height: 18,
      color: "#9d7dff",
    },
    style: {
      stroke: "#9d7dff",
      strokeWidth: 2,
    },
    pathOptions: {
      borderRadius: 12,
      offset: 18,
    },
  }));
}

async function buildDetailedLayout(model: DiagramModel): Promise<{ nodes: Node[]; edges: Edge[] }> {
  const positions = new Map<string, { x: number; y: number }>();
  const centerX = 470;
  const leftX = 70;
  const rightX = 870;
  const linearStepGap = 180;
  const branchBlockHeight = 420;
  let currentMainY = 0;

  const stepNodeIds = model.nodes
    .map((node) => node.id)
    .filter((id) => id.startsWith("s"))
    .sort((a, b) => Number(a.slice(1)) - Number(b.slice(1)));

  for (const stepNodeId of stepNodeIds) {
    const stepIndex = Number(stepNodeId.slice(1));
    const hasBranch = model.nodes.some((node) => node.id === `d${stepIndex}`);

    positions.set(stepNodeId, { x: centerX, y: currentMainY });

    if (!hasBranch) {
      currentMainY += linearStepGap;
      continue;
    }

    positions.set(`d${stepIndex}`, { x: centerX, y: currentMainY + 110 });
    positions.set(`c${stepIndex}`, { x: leftX, y: currentMainY + 145 });
    positions.set(`r${stepIndex}`, { x: leftX, y: currentMainY + 275 });
    positions.set(`m${stepIndex}`, { x: rightX, y: currentMainY + 205 });

    currentMainY += branchBlockHeight;
  }

  if (model.nodes.some((node) => node.id === "end")) {
    positions.set("end", { x: centerX, y: currentMainY + 20 });
  }

  const nodes: Node[] = model.nodes.map((node, zeroBasedIndex) => {
    const category = zeroBasedIndex === 0 ? "start" : node.category;
    const position = positions.get(node.id) ?? { x: centerX, y: zeroBasedIndex * linearStepGap };

    return {
      id: node.id,
      type: category,
      position,
      sourcePosition: category === "decision" ? Position.Right : Position.Bottom,
      targetPosition: category === "decision" ? Position.Top : Position.Top,
      data: {
        label: zeroBasedIndex === 0 ? `Start\n${node.label}` : node.label,
        stepRange: node.stepRange,
        category,
        viewType: model.viewType,
      },
      style: {
        width: getNodeWidth(node),
        minHeight: getNodeHeight(node, zeroBasedIndex === 0 ? `Start\n${node.label}` : node.label, category),
      },
    };
  });

  const edges: Edge[] = model.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label,
    type: "smoothstep",
    animated: false,
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 18,
      height: 18,
      color: "#9d7dff",
    },
    style: {
      stroke: "#9d7dff",
      strokeWidth: 2,
    },
    pathOptions: {
      borderRadius: 18,
      offset: 26,
    },
    sourceHandle: edge.sourceHandle,
    targetHandle: edge.targetHandle,
  }));

  return { nodes, edges };
}

function applySavedPositions(nodes: Node[], savedPositions: DiagramLayoutNodePosition[]): Node[] {
  const savedPositionMap = new Map(savedPositions.map((node) => [node.id, { x: node.x, y: node.y, label: node.label, width: node.width, height: node.height }]));
  return nodes.map((node) => ({
    ...node,
    position: savedPositionMap.get(node.id)
      ? {
          x: savedPositionMap.get(node.id)!.x,
          y: savedPositionMap.get(node.id)!.y,
        }
      : node.position,
    data:
      savedPositionMap.get(node.id)?.label && typeof node.data === "object"
        ? {
            ...node.data,
            label: savedPositionMap.get(node.id)!.label,
          }
        : node.data,
    style:
      savedPositionMap.get(node.id)?.width || savedPositionMap.get(node.id)?.height
        ? {
            ...(node.style ?? {}),
            width: savedPositionMap.get(node.id)?.width ?? node.style?.width,
            minHeight: savedPositionMap.get(node.id)?.height ?? node.style?.minHeight,
          }
        : node.style,
  }));
}

export async function buildFlowchartLayout(
  model: DiagramModel,
  savedPositions: DiagramLayoutNodePosition[] = [],
): Promise<{ nodes: Node[]; edges: Edge[] }> {
  if (model.viewType === "detailed") {
    const layout = await buildDetailedLayout(model);
    return {
      nodes: applySavedPositions(layout.nodes, savedPositions),
      edges: layout.edges,
    };
  }

  const overviewNodes = applySavedPositions(buildOverviewNodes(model), savedPositions);
  return {
    nodes: overviewNodes,
    edges: buildOverviewEdges(model, overviewNodes),
  };
}

export function withUpdatedNodeLabel(nodes: Node[], nodeId: string, value: string): Node[] {
  return nodes.map((node) =>
    node.id === nodeId
      ? {
          ...node,
          data: {
            ...(typeof node.data === "object" && node.data ? node.data : {}),
            label: value,
          },
          style: {
            ...(node.style ?? {}),
            minHeight: estimateNodeMinHeight(
              value,
              typeof node.data === "object" && node.data && "category" in node.data ? String(node.data.category ?? "process") : "process",
            ),
          },
        }
      : node,
  );
}
