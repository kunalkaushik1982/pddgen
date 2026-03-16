/**
 * Purpose: Read-only React Flow preview for backend-generated flowchart models.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\diagram\FlowchartPreviewPanel.tsx
 */

import React, { useEffect, useState } from "react";
import { toPng } from "html-to-image";
import ReactFlow, {
  Background,
  type Connection,
  Controls,
  MarkerType,
  applyNodeChanges,
  type Edge,
  type Node,
  type NodeChange,
  type ReactFlowInstance,
} from "reactflow";
import "reactflow/dist/style.css";

import { diagramEdgeTypes } from "./EditableEdge";
import { diagramNodeTypes } from "./DiagramNodes";
import { buildFlowchartLayout, snapNodePositions, withAutoConnectionHandles, withUpdatedNodeLabel } from "./diagramLayout";
import { apiClient } from "../../services/apiClient";
import {
  DEFAULT_DIAGRAM_CANVAS_SETTINGS,
  type DiagramCanvasSettings,
  type DiagramLayoutNodePosition,
  type DiagramModel,
} from "../../types/diagram";
import type { DraftSession } from "../../types/session";

type FlowchartPreviewPanelProps = {
  session: DraftSession;
  allowEditing?: boolean;
  onSessionRefresh?: () => Promise<void> | void;
};

type DiagramHistoryState = {
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string;
  selectedEdgeId: string;
  pendingConnectorSourceId: string;
};

type InspectorMode = "pinned" | "floating" | "collapsed";

export function FlowchartPreviewPanel({
  session,
  allowEditing = false,
  onSessionRefresh,
}: FlowchartPreviewPanelProps): JSX.Element | null {
  const [diagram, setDiagram] = useState<DiagramModel | null>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSavingLayout, setIsSavingLayout] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [diagramContainer, setDiagramContainer] = useState<HTMLDivElement | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [selectedEdgeId, setSelectedEdgeId] = useState("");
  const [pendingConnectorSourceId, setPendingConnectorSourceId] = useState("");
  const [undoStack, setUndoStack] = useState<DiagramHistoryState[]>([]);
  const [redoStack, setRedoStack] = useState<DiagramHistoryState[]>([]);
  const [inspectorMode, setInspectorMode] = useState<InspectorMode>("pinned");
  const [flowInstance, setFlowInstance] = useState<ReactFlowInstance | null>(null);
  const [canvasSettings, setCanvasSettings] = useState<DiagramCanvasSettings>(DEFAULT_DIAGRAM_CANVAS_SETTINGS);
  const savedDiagramArtifact = session.inputArtifacts.find(
    (artifact) => artifact.kind === "diagram" && artifact.name === "detailed-process-flow.png",
  );

  function attachNodeEditing(nextNodes: Node[]): Node[] {
    return nextNodes.map((node) => ({
      ...node,
      data: {
        ...(typeof node.data === "object" && node.data ? node.data : {}),
        canvasTheme: canvasSettings.theme,
        editable: allowEditing,
        onLabelChange: (value: string) => handleNodeLabelChange(node.id, value),
        selected: node.id === selectedNodeId,
        connectorSource: node.id === pendingConnectorSourceId,
      },
    }));
  }

  function attachEdgeEditing(nextEdges: Edge[], nextNodes: Node[] = nodes): Edge[] {
    return withAutoConnectionHandles(nextNodes, nextEdges).map((edge) => ({
      ...edge,
      type: "editable",
      label: typeof edge.label === "string" ? edge.label : "",
      data: {
        ...(typeof edge.data === "object" && edge.data ? edge.data : {}),
        editable: allowEditing,
        selected: edge.id === selectedEdgeId,
        onLabelChange: (value: string) => handleEdgeLabelChange(edge.id, value),
      },
      style: {
        ...(edge.style ?? {}),
        stroke: edge.id === selectedEdgeId ? "#ffd666" : "#9d7dff",
        strokeWidth: edge.id === selectedEdgeId ? 3 : 2,
      },
    }));
  }

  function snapshotNodes(nextNodes: Node[]): Node[] {
    return nextNodes.map((node) => ({
      id: node.id,
      type: node.type,
      position: { x: node.position.x, y: node.position.y },
      sourcePosition: node.sourcePosition,
      targetPosition: node.targetPosition,
      width: node.width,
      height: node.height,
      data:
        typeof node.data === "object" && node.data
          ? {
              label: "label" in node.data ? String(node.data.label ?? "") : "",
              stepRange: "stepRange" in node.data ? String(node.data.stepRange ?? "") : "",
              category: "category" in node.data ? String(node.data.category ?? "process") : "process",
              viewType: "viewType" in node.data ? node.data.viewType : "detailed",
            }
          : {},
      style: node.style,
    } as Node));
  }

  function snapshotEdges(nextEdges: Edge[]): Edge[] {
    return nextEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: typeof edge.label === "string" ? edge.label : "",
      type: edge.type,
      animated: edge.animated,
      markerEnd: edge.markerEnd,
      pathOptions: (edge as Edge & { pathOptions?: unknown }).pathOptions,
      sourceHandle: edge.sourceHandle,
      targetHandle: edge.targetHandle,
      style: edge.style,
    } as Edge));
  }

  function buildHistoryState(
    currentNodes: Node[],
    currentEdges: Edge[],
    currentSelectedNodeId = selectedNodeId,
    currentSelectedEdgeId = selectedEdgeId,
    currentPendingConnectorSourceId = pendingConnectorSourceId,
  ): DiagramHistoryState {
    return {
      nodes: snapshotNodes(currentNodes),
      edges: snapshotEdges(currentEdges),
      selectedNodeId: currentSelectedNodeId,
      selectedEdgeId: currentSelectedEdgeId,
      pendingConnectorSourceId: currentPendingConnectorSourceId,
    };
  }

  function restoreHistoryState(state: DiagramHistoryState) {
    setSelectedNodeId(state.selectedNodeId);
    setSelectedEdgeId(state.selectedEdgeId);
    setPendingConnectorSourceId(state.pendingConnectorSourceId);
    const restoredNodes = attachNodeEditing(state.nodes);
    setNodes(restoredNodes);
    setEdges(attachEdgeEditing(state.edges, restoredNodes));
  }

  function rememberForUndo(currentNodes = nodes, currentEdges = edges) {
    const snapshot = buildHistoryState(currentNodes, currentEdges);
    setUndoStack((previous) => [...previous.slice(-49), snapshot]);
    setRedoStack([]);
  }

  useEffect(() => {
    if (session.diagramType !== "flowchart") {
      setDiagram(null);
      setNodes([]);
      setEdges([]);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setErrorMessage("");

    void apiClient
      .getDiagramModel(session.id, "detailed")
      .then(async (model) => {
        if (!isMounted) {
          return;
        }
        setDiagram(model);
        const savedLayout = await apiClient.getDiagramLayout(session.id, "detailed");
        const layout = await buildFlowchartLayout(model, savedLayout.nodes);
        if (!isMounted) {
          return;
        }
        setCanvasSettings(savedLayout.canvasSettings);
        const preparedNodes = attachNodeEditing(layout.nodes);
        setNodes(preparedNodes);
        setEdges(attachEdgeEditing(layout.edges, preparedNodes));
        setSelectedNodeId("");
        setSelectedEdgeId("");
        setPendingConnectorSourceId("");
        setUndoStack([]);
        setRedoStack([]);
      })
      .catch((error) => {
        if (!isMounted) {
          return;
        }
        setErrorMessage(error instanceof Error ? error.message : "Diagram preview could not be loaded.");
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [allowEditing, session.diagramType, session.id]);

  useEffect(() => {
    setNodes((currentNodes) => attachNodeEditing(currentNodes));
  }, [selectedNodeId, pendingConnectorSourceId, allowEditing]);

  useEffect(() => {
    setEdges((currentEdges) => attachEdgeEditing(currentEdges));
  }, [selectedEdgeId]);

  useEffect(() => {
    if (!flowInstance || nodes.length === 0) {
      return;
    }
    const timerId = window.setTimeout(() => {
      flowInstance.fitView({ padding: inspectorMode === "pinned" ? 0.24 : 0.2, duration: 250 });
    }, 80);
    return () => window.clearTimeout(timerId);
  }, [flowInstance, inspectorMode, nodes.length]);

  if (session.diagramType !== "flowchart") {
    return null;
  }

  function handleNodesChange(changes: NodeChange[]) {
    if (!allowEditing) {
      return;
    }
    rememberForUndo();
    setNodes((currentNodes) => {
      const updatedNodes = attachNodeEditing(snapNodePositions(applyNodeChanges(changes, currentNodes)));
      setEdges((currentEdges) => attachEdgeEditing(currentEdges, updatedNodes));
      return updatedNodes;
    });
  }

  function handleNodeLabelChange(nodeId: string, value: string) {
    rememberForUndo();
    setNodes((currentNodes) => attachNodeEditing(withUpdatedNodeLabel(currentNodes, nodeId, value)));
  }

  function handleNodeSelect(node: Node) {
    setSelectedNodeId(node.id);
    setSelectedEdgeId("");
  }

  function handleEdgeSelect(edge: Edge) {
    setSelectedEdgeId(edge.id);
    setSelectedNodeId("");
  }

  const selectedNode = selectedNodeId ? nodes.find((node) => node.id === selectedNodeId) ?? null : null;
  const selectedEdge = selectedEdgeId ? edges.find((edge) => edge.id === selectedEdgeId) ?? null : null;

  function buildEditableDiagramModel(currentNodes: Node[], currentEdges: Edge[]): DiagramModel | null {
    if (!diagram) {
      return null;
    }
    return {
      diagramType: diagram.diagramType,
      viewType: "detailed",
      title: diagram.title,
      nodes: currentNodes.map((node, index) => {
        const categoryFromData =
          typeof node.data === "object" && node.data && "category" in node.data ? String(node.data.category ?? "process") : "process";
        const normalizedCategory = index === 0 ? "start" : categoryFromData;
        return {
          id: node.id,
          label: typeof node.data === "object" && node.data && "label" in node.data ? String(node.data.label ?? "") : "",
          category: normalizedCategory as DiagramModel["nodes"][number]["category"],
          stepRange: typeof node.data === "object" && node.data && "stepRange" in node.data ? String(node.data.stepRange ?? "") : "",
          width: typeof node.width === "number" ? node.width : typeof node.style?.width === "number" ? node.style.width : undefined,
          height:
            typeof node.height === "number"
              ? node.height
              : typeof node.style?.minHeight === "number"
                ? node.style.minHeight
                : undefined,
        };
      }),
      edges: currentEdges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: typeof edge.label === "string" ? edge.label : "",
        sourceHandle: edge.sourceHandle ?? undefined,
        targetHandle: edge.targetHandle ?? undefined,
      })),
    };
  }

  function handleDeleteSelectedNode() {
    if (!selectedNodeId) {
      return;
    }
    const selectedNode = nodes.find((node) => node.id === selectedNodeId);
    if (!selectedNode) {
      return;
    }
    const selectedCategory =
      typeof selectedNode.data === "object" && selectedNode.data && "category" in selectedNode.data ? String(selectedNode.data.category ?? "") : "";
    if (selectedCategory === "start") {
      setErrorMessage("Start node cannot be deleted.");
      return;
    }
    rememberForUndo();
    setNodes((currentNodes) => attachNodeEditing(currentNodes.filter((node) => node.id !== selectedNodeId)));
    setEdges((currentEdges) => attachEdgeEditing(currentEdges.filter((edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId)));
    if (pendingConnectorSourceId === selectedNodeId) {
      setPendingConnectorSourceId("");
    }
    setSelectedNodeId("");
  }

  function handleDuplicateSelectedNode() {
    if (!selectedNodeId) {
      return;
    }
    const sourceNode = nodes.find((node) => node.id === selectedNodeId);
    if (!sourceNode) {
      return;
    }
    const duplicatedId = `${sourceNode.id}_copy_${Date.now()}`;
    const duplicatedLabel =
      typeof sourceNode.data === "object" && sourceNode.data && "label" in sourceNode.data ? String(sourceNode.data.label ?? "") : "Copied step";
    const duplicatedStepRange =
      typeof sourceNode.data === "object" && sourceNode.data && "stepRange" in sourceNode.data ? String(sourceNode.data.stepRange ?? "") : "";
    const sourceCategory =
      typeof sourceNode.data === "object" && sourceNode.data && "category" in sourceNode.data ? String(sourceNode.data.category ?? "process") : "process";
    const duplicatedCategory = sourceCategory === "start" ? "process" : sourceCategory;

    const duplicatedNode: Node = {
      ...sourceNode,
      id: duplicatedId,
      type: duplicatedCategory,
      position: {
        x: sourceNode.position.x + 60,
        y: sourceNode.position.y + 60,
      },
      data: {
        ...(typeof sourceNode.data === "object" && sourceNode.data ? sourceNode.data : {}),
        label: duplicatedLabel,
        stepRange: duplicatedStepRange,
        category: duplicatedCategory,
      },
    };

    rememberForUndo();
    setNodes((currentNodes) => attachNodeEditing([...currentNodes, duplicatedNode]));
    setSelectedNodeId(duplicatedId);
  }

  function handleAddNode(category: "process" | "decision") {
    rememberForUndo();
    const averageX = nodes.length > 0 ? nodes.reduce((sum, node) => sum + node.position.x, 0) / nodes.length : 420;
    const averageY = nodes.length > 0 ? nodes.reduce((sum, node) => sum + node.position.y, 0) / nodes.length : 180;
    const nextId = `manual_${category}_${Date.now()}`;
    const nextLabel = category === "decision" ? "Decision" : "Process step";
    const nextNode: Node = {
      id: nextId,
      type: category,
      position: {
        x: averageX + 80,
        y: averageY + 60,
      },
      sourcePosition: category === "decision" ? undefined : undefined,
      targetPosition: category === "decision" ? undefined : undefined,
      data: {
        label: nextLabel,
        stepRange: "",
        category,
        viewType: "detailed",
      },
      style: {
        width: category === "decision" ? 160 : 220,
        minHeight: category === "decision" ? 160 : 84,
        },
      };
      setNodes((currentNodes) => attachNodeEditing([...currentNodes, nextNode]));
      setSelectedNodeId(nextId);
      setSelectedEdgeId("");
      window.setTimeout(() => {
        flowInstance?.setCenter(nextNode.position.x + 110, nextNode.position.y + 60, {
          zoom: 1.1,
          duration: 250,
        });
      }, 0);
    }

  function handleStartConnector() {
    if (!selectedNodeId) {
      return;
    }
    setPendingConnectorSourceId(selectedNodeId);
    setErrorMessage("");
  }

  function handleConnectToSelected() {
    if (!pendingConnectorSourceId || !selectedNodeId || pendingConnectorSourceId === selectedNodeId) {
      return;
    }
    rememberForUndo();
    const edgeId = `manual_${pendingConnectorSourceId}_${selectedNodeId}_${Date.now()}`;
    setEdges((currentEdges) => {
      const alreadyExists = currentEdges.some((edge) => edge.source === pendingConnectorSourceId && edge.target === selectedNodeId);
      if (alreadyExists) {
        return attachEdgeEditing(currentEdges);
      }
      return attachEdgeEditing([
        ...currentEdges,
        {
          id: edgeId,
          source: pendingConnectorSourceId,
          target: selectedNodeId,
          label: "",
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
        } as Edge,
      ]);
    });
    setPendingConnectorSourceId("");
  }

  function handleConnect(connection: Connection) {
    if (!allowEditing || !connection.source || !connection.target || connection.source === connection.target) {
      return;
    }
    rememberForUndo();
    const edgeId = `manual_${connection.source}_${connection.target}_${Date.now()}`;
    setEdges((currentEdges) => {
      const alreadyExists = currentEdges.some(
        (edge) =>
          edge.source === connection.source &&
          edge.target === connection.target &&
          edge.sourceHandle === connection.sourceHandle &&
          edge.targetHandle === connection.targetHandle,
      );
      if (alreadyExists) {
        return attachEdgeEditing(currentEdges);
      }
      return attachEdgeEditing([
        ...currentEdges,
        {
          id: edgeId,
          source: connection.source,
          target: connection.target,
          sourceHandle: connection.sourceHandle,
          targetHandle: connection.targetHandle,
          label: "",
          type: "editable",
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
        } as Edge,
      ]);
    });
    setPendingConnectorSourceId("");
    setSelectedNodeId("");
    setSelectedEdgeId(edgeId);
  }

  function handleDeleteSelectedConnector() {
    if (!selectedEdgeId) {
      return;
    }
    rememberForUndo();
    setEdges((currentEdges) => attachEdgeEditing(currentEdges.filter((edge) => edge.id !== selectedEdgeId)));
    setSelectedEdgeId("");
  }

  function handleEdgeLabelChange(edgeId: string, value: string) {
    rememberForUndo();
    setEdges((currentEdges) =>
      attachEdgeEditing(
        currentEdges.map((edge) =>
          edge.id === edgeId
            ? {
                ...edge,
                label: value,
              }
            : edge,
        ),
      ),
    );
  }

  async function handleResetLayout() {
    if (!diagram) {
      return;
    }
    rememberForUndo();
    setErrorMessage("");
    const layout = await buildFlowchartLayout(diagram, []);
    setNodes(attachNodeEditing(layout.nodes));
    setEdges(attachEdgeEditing(layout.edges, layout.nodes));
    setSelectedNodeId("");
    setSelectedEdgeId("");
    setPendingConnectorSourceId("");
  }

  useEffect(() => {
    if (!allowEditing) {
      return;
    }
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        (target instanceof HTMLElement && target.isContentEditable)
      ) {
        return;
      }
      if (event.key !== "Delete" && event.key !== "Backspace") {
        return;
      }
      if (selectedEdgeId) {
        event.preventDefault();
        handleDeleteSelectedConnector();
        return;
      }
      if (selectedNodeId) {
        event.preventDefault();
        handleDeleteSelectedNode();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [allowEditing, selectedEdgeId, selectedNodeId, nodes, edges]);

  function handleUndo() {
    if (undoStack.length === 0) {
      return;
    }
    const previous = undoStack[undoStack.length - 1];
    const current = buildHistoryState(nodes, edges);
    setUndoStack((stack) => stack.slice(0, -1));
    setRedoStack((stack) => [...stack, current]);
    restoreHistoryState(previous);
  }

  function handleRedo() {
    if (redoStack.length === 0) {
      return;
    }
    const next = redoStack[redoStack.length - 1];
    const current = buildHistoryState(nodes, edges);
    setRedoStack((stack) => stack.slice(0, -1));
    setUndoStack((stack) => [...stack.slice(-49), current]);
    restoreHistoryState(next);
  }

  async function handleSaveLayout() {
    if (!allowEditing) {
      return;
    }
    setIsSavingLayout(true);
    setErrorMessage("");
    try {
      const currentDiagramModel = buildEditableDiagramModel(nodes, edges);
      if (!currentDiagramModel) {
        throw new Error("Diagram model is not available.");
      }
      await apiClient.saveDiagramModel(session.id, currentDiagramModel);
      await apiClient.saveDiagramLayout(
        session.id,
        nodes.map((node) => ({
          id: node.id,
          x: node.position.x,
          y: node.position.y,
          label: typeof node.data === "object" && node.data && "label" in node.data ? String(node.data.label ?? "") : "",
          width: typeof node.width === "number" ? node.width : typeof node.style?.width === "number" ? node.style.width : undefined,
          height:
            typeof node.height === "number"
              ? node.height
              : typeof node.style?.minHeight === "number"
                ? node.style.minHeight
                : undefined,
        })),
        "balanced",
        canvasSettings,
        "detailed",
      );
      if (!diagramContainer) {
        throw new Error("Diagram canvas is not available for export.");
      }
      const imageDataUrl = await toPng(diagramContainer, {
        cacheBust: true,
        pixelRatio: 2.5,
        backgroundColor:
          canvasSettings.theme === "light"
            ? "#f7f3ff"
            : canvasSettings.theme === "blueprint"
              ? "#11346b"
              : canvasSettings.theme === "plain"
                ? "#191427"
                : "#140d24",
      });
      await apiClient.saveDiagramArtifact(session.id, imageDataUrl);
      await onSessionRefresh?.();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Layout could not be saved.");
    } finally {
      setIsSavingLayout(false);
    }
  }

  const backgroundColor =
    canvasSettings.theme === "light"
      ? "#c7bedf"
      : canvasSettings.theme === "blueprint"
        ? "#9ed0ff"
        : canvasSettings.theme === "plain"
          ? "#7d6aa8"
          : "#6f59b3";
  const canvasClassName = `diagram-preview-canvas diagram-preview-canvas-detailed diagram-preview-canvas-theme-${canvasSettings.theme}`;
  const inspectorClassName = `diagram-inspector diagram-inspector-theme-${canvasSettings.theme} ${inspectorMode === "floating" ? "diagram-inspector-floating" : ""}`;

  return (
    <section className="stack diagram-preview-panel">
      <div className="diagram-toolbar">
        {allowEditing ? (
          <button type="button" className="button-secondary" onClick={() => void handleSaveLayout()} disabled={isSavingLayout}>
            {isSavingLayout ? "Saving layout..." : "Save diagram layout"}
          </button>
        ) : null}
        {allowEditing ? (
          <button type="button" className="button-secondary" onClick={handleUndo} disabled={undoStack.length === 0 || isSavingLayout}>
            Undo
          </button>
        ) : null}
        {allowEditing ? (
          <button type="button" className="button-secondary" onClick={handleRedo} disabled={redoStack.length === 0 || isSavingLayout}>
            Redo
          </button>
        ) : null}
        {allowEditing ? (
          <button type="button" className="button-secondary" onClick={() => void handleResetLayout()} disabled={isSavingLayout || isLoading}>
            Reset to auto-layout
          </button>
        ) : null}
        <div className="diagram-toolbar-spacer" />
        {allowEditing ? (
          <>
            <button
              type="button"
              className="button-secondary"
              onClick={() => setInspectorMode((current) => (current === "pinned" ? "floating" : "pinned"))}
            >
              {inspectorMode === "pinned" ? "Undock" : "Dock"}
            </button>
          </>
        ) : null}
      </div>

      {isLoading ? <div className="empty-state">Loading flowchart preview...</div> : null}
      {errorMessage ? <div className="message-banner error">{errorMessage}</div> : null}

      {!isLoading && !errorMessage && diagram ? (
        <div className="diagram-preview-shell">
          <div className="artifact-meta">
            detailed | {diagram.nodes.length} node(s) | {diagram.edges.length} edge(s)
          </div>
          <div className={`diagram-editor-layout ${inspectorMode === "pinned" ? "diagram-editor-layout-pinned" : ""}`}>
            <div className="diagram-canvas-stack">
              {!allowEditing && savedDiagramArtifact ? (
                <div className={`${canvasClassName} diagram-preview-image-shell`}>
                  <img
                    className="diagram-preview-image"
                    src={apiClient.getArtifactContentUrl(savedDiagramArtifact.id)}
                    alt="Saved process diagram preview"
                  />
                </div>
              ) : (
                <div className={canvasClassName} ref={setDiagramContainer}>
                  <ReactFlow
                    fitView
                    fitViewOptions={{ padding: 0.2 }}
                    onInit={setFlowInstance}
                    nodes={nodes}
                    edges={edges}
                    edgeTypes={diagramEdgeTypes}
                    nodeTypes={diagramNodeTypes}
                    onNodesChange={handleNodesChange}
                    onConnect={handleConnect}
                    onNodeClick={(_, node) => handleNodeSelect(node)}
                    onEdgeClick={(_, edge) => handleEdgeSelect(edge)}
                    onPaneClick={() => {
                      setSelectedNodeId("");
                      setSelectedEdgeId("");
                    }}
                    nodesDraggable={allowEditing}
                    nodesConnectable={allowEditing}
                    elementsSelectable={false}
                  >
                    <Controls showInteractive={false} />
                    {canvasSettings.showGrid ? <Background gap={22} size={1.1} color={backgroundColor} /> : null}
                  </ReactFlow>
                </div>
              )}
            </div>

            {allowEditing && inspectorMode === "collapsed" ? (
              <button
                type="button"
                className="diagram-inspector-tab"
                onClick={() => setInspectorMode("pinned")}
              >
                Inspector
              </button>
            ) : null}

            {allowEditing && inspectorMode !== "collapsed" ? (
              <aside className={inspectorClassName}>
                <div className="diagram-inspector-header">
                  <strong>Inspector</strong>
                  <div className="artifact-meta">
                    {selectedNode ? "Node" : selectedEdge ? "Connector" : "Tools"}
                  </div>
                </div>

                {selectedNode ? (
                  <div className="diagram-inspector-section stack">
                      <div className="button-row">
                        <button type="button" className="button-secondary" onClick={handleDuplicateSelectedNode} disabled={isSavingLayout} title="Duplicate block">
                          Duplicate
                        </button>
                        <button type="button" className="button-secondary" onClick={handleDeleteSelectedNode} disabled={isSavingLayout} title="Delete block">
                          Delete
                        </button>
                      </div>
                      <div className="button-row">
                        <button
                          type="button"
                          className="button-secondary"
                          onClick={handleStartConnector}
                          disabled={isSavingLayout}
                          title={pendingConnectorSourceId ? "Change source" : "Set source"}
                        >
                          {pendingConnectorSourceId ? "Change source" : "Set source"}
                        </button>
                        <button
                          type="button"
                          className="button-secondary"
                          onClick={handleConnectToSelected}
                          disabled={!pendingConnectorSourceId || pendingConnectorSourceId === selectedNodeId || isSavingLayout}
                          title="Connect source to this block"
                        >
                          Connect
                        </button>
                      </div>
                    </div>
                  ) : null}

                  {selectedEdge ? (
                    <div className="diagram-inspector-section stack">
                      <div className="button-row">
                        <button type="button" className="button-secondary" onClick={handleDeleteSelectedConnector} disabled={isSavingLayout} title="Delete connector">
                          Delete edge
                        </button>
                      </div>
                    </div>
                  ) : null}

                  {!selectedNode && !selectedEdge ? (
                    <div className="diagram-inspector-section stack">
                      <div className="diagram-inspector-subtitle">Canvas</div>
                      <label className="diagram-inspector-field">
                        <span>Theme</span>
                        <select
                          value={canvasSettings.theme}
                          onChange={(event) =>
                            setCanvasSettings((current) => ({
                              ...current,
                              theme: event.target.value as DiagramCanvasSettings["theme"],
                            }))
                          }
                        >
                          <option value="dark">Dark</option>
                          <option value="light">Light</option>
                          <option value="blueprint">Blueprint</option>
                          <option value="plain">Plain</option>
                        </select>
                      </label>
                      <label className="diagram-inspector-toggle">
                        <input
                          type="checkbox"
                          checked={canvasSettings.showGrid}
                          onChange={(event) =>
                            setCanvasSettings((current) => ({
                              ...current,
                              showGrid: event.target.checked,
                            }))
                          }
                        />
                        <span>Show grid</span>
                      </label>
                      <div className="diagram-inspector-subtitle">Blocks</div>
                      <div className="button-row">
                        <button type="button" className="button-secondary" onClick={() => handleAddNode("process")} disabled={isSavingLayout} title="Add process block">
                          Add process
                        </button>
                        <button type="button" className="button-secondary" onClick={() => handleAddNode("decision")} disabled={isSavingLayout} title="Add decision block">
                          Add decision
                        </button>
                      </div>
                    </div>
                  ) : null}
              </aside>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}
