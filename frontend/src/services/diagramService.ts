import type {
  DiagramCanvasSettings,
  DiagramExportPreset,
  DiagramLayoutNodePosition,
  DiagramModel,
} from "../types/diagram";
import type { DraftSession } from "../types/session";
import type { BackendDiagramLayoutResponse, BackendDiagramModel, BackendDraftSession } from "./contracts";
import { fetchJson } from "./http";
import { mapDiagramLayout, mapDiagramModel, mapDraftSession } from "./mappers";

export const diagramService = {
  async getDiagramModel(sessionId: string, viewType: DiagramModel["viewType"] = "overview"): Promise<DiagramModel> {
    const diagram = await fetchJson<BackendDiagramModel>(`/draft-sessions/${sessionId}/diagram-model?view=${viewType}`);
    return mapDiagramModel(diagram);
  },

  async saveDiagramModel(sessionId: string, model: DiagramModel): Promise<DiagramModel> {
    const diagram = await fetchJson<BackendDiagramModel>(`/draft-sessions/${sessionId}/diagram-model?view=${model.viewType}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: model.title,
        view_type: model.viewType,
        nodes: model.nodes.map((node) => ({
          id: node.id,
          label: node.label,
          category: node.category,
          step_range: node.stepRange,
          width: node.width,
          height: node.height,
        })),
        edges: model.edges.map((edge) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.label,
          source_handle: edge.sourceHandle,
          target_handle: edge.targetHandle,
        })),
      }),
    });
    return mapDiagramModel(diagram);
  },

  async getDiagramLayout(
    sessionId: string,
    viewType: DiagramModel["viewType"] = "detailed",
  ): Promise<{ nodes: DiagramLayoutNodePosition[]; exportPreset: DiagramExportPreset; canvasSettings: DiagramCanvasSettings }> {
    const layout = await fetchJson<BackendDiagramLayoutResponse>(`/draft-sessions/${sessionId}/diagram-layout?view=${viewType}`);
    return mapDiagramLayout(layout);
  },

  async saveDiagramLayout(
    sessionId: string,
    nodes: DiagramLayoutNodePosition[],
    exportPreset: DiagramExportPreset,
    canvasSettings: DiagramCanvasSettings,
    viewType: DiagramModel["viewType"] = "detailed",
  ): Promise<{ nodes: DiagramLayoutNodePosition[]; exportPreset: DiagramExportPreset; canvasSettings: DiagramCanvasSettings }> {
    const layout = await fetchJson<BackendDiagramLayoutResponse>(`/draft-sessions/${sessionId}/diagram-layout?view=${viewType}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nodes,
        export_preset: exportPreset,
        canvas_settings: {
          theme: canvasSettings.theme,
          show_grid: canvasSettings.showGrid,
          grid_density: canvasSettings.gridDensity,
        },
      }),
    });
    return mapDiagramLayout(layout);
  },

  async saveDiagramArtifact(sessionId: string, imageDataUrl: string): Promise<DraftSession> {
    const session = await fetchJson<BackendDraftSession>(`/draft-sessions/${sessionId}/diagram-artifact`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_data_url: imageDataUrl }),
    });
    return mapDraftSession(session);
  },
};
