/**
 * Purpose: Layout helpers for overview and detailed flowchart previews.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\diagram\diagramLayout.ts
 */

import ELK from "elkjs/lib/elk.bundled.js";
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
const elk = new ELK();

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

function buildNodeData(model: DiagramModel, node: DiagramModel["nodes"][number], zeroBasedIndex: number): Node {
  const category = zeroBasedIndex === 0 ? "start" : node.category;
  const label = zeroBasedIndex === 0 ? `Start\n${node.label}` : node.label;

  return {
    id: node.id,
    type: category,
    position: { x: 0, y: 0 },
    sourcePosition: category === "decision" ? Position.Right : Position.Bottom,
    targetPosition: Position.Top,
    data: {
      label,
      stepRange: node.stepRange,
      category,
      viewType: model.viewType,
    },
    style: {
      width: getNodeWidth(node),
      minHeight: getNodeHeight(node, label, category),
    },
  };
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
  const fallbackNodes: Node[] = model.nodes.map((node, zeroBasedIndex) => ({
    ...buildNodeData(model, node, zeroBasedIndex),
    position: {
      x: 470,
      y: zeroBasedIndex * 180,
    },
  }));

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

  try {
    const elkLayout = await elk.layout({
      id: "root",
      layoutOptions: {
        "elk.algorithm": "layered",
        "elk.direction": "DOWN",
        "elk.spacing.nodeNode": "100",
        "elk.layered.spacing.nodeNodeBetweenLayers": "140",
        "elk.spacing.edgeNode": "48",
        "elk.edgeRouting": "ORTHOGONAL",
        "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
        "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
        "elk.contentAlignment": "[H_CENTER, V_TOP]",
      },
      children: model.nodes.map((node, zeroBasedIndex) => {
        const reactFlowNode = buildNodeData(model, node, zeroBasedIndex);
        return {
          id: node.id,
          width: getRenderedNodeWidth(reactFlowNode),
          height: getRenderedNodeHeight(reactFlowNode),
        };
      }),
      edges: model.edges.map((edge) => ({
        id: edge.id,
        sources: [edge.source],
        targets: [edge.target],
      })),
    });

    const positionedNodes = fallbackNodes.map((node) => {
      const elkNode = elkLayout.children?.find((child) => child.id === node.id);
      if (!elkNode) {
        return node;
      }
      return {
        ...node,
        position: {
          x: snapToGrid(elkNode.x ?? node.position.x),
          y: snapToGrid(elkNode.y ?? node.position.y),
        },
      };
    });

    return { nodes: positionedNodes, edges };
  } catch {
    return { nodes: fallbackNodes, edges };
  }
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
