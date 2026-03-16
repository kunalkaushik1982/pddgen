/**
 * Purpose: Shared frontend types for previewable process diagrams.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\types\diagram.ts
 */

export type DiagramNode = {
  id: string;
  label: string;
  category: "process" | "decision" | "empty" | "start" | "terminal";
  stepRange: string;
  width?: number;
  height?: number;
};

export type DiagramEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
  sourceHandle?: string;
  targetHandle?: string;
};

export type DiagramLayoutNodePosition = {
  id: string;
  x: number;
  y: number;
  label?: string;
  width?: number;
  height?: number;
};

export type DiagramCanvasTheme = "dark" | "light" | "blueprint" | "plain";
export type DiagramGridDensity = "fine" | "medium" | "wide";

export type DiagramCanvasSettings = {
  theme: DiagramCanvasTheme;
  showGrid: boolean;
  gridDensity: DiagramGridDensity;
};

export type DiagramExportPreset = "compact" | "balanced" | "readable";

export const DEFAULT_DIAGRAM_CANVAS_SETTINGS: DiagramCanvasSettings = {
  theme: "dark",
  showGrid: true,
  gridDensity: "medium",
};

export type DiagramModel = {
  diagramType: "flowchart" | "sequence";
  viewType: "overview" | "detailed";
  title: string;
  nodes: DiagramNode[];
  edges: DiagramEdge[];
};
