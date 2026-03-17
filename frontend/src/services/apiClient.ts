/**
 * Purpose: Typed frontend API client for upload, generation, review, and export.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\services\apiClient.ts
 */

import type { User } from "../types/auth";
import type {
  DiagramCanvasSettings,
  DiagramExportPreset,
  DiagramLayoutNodePosition,
  DiagramModel,
} from "../types/diagram";
import type { CandidateScreenshot, ProcessNote, ProcessStep, StepScreenshot } from "../types/process";
import type { ActionLogEntry, DraftSession, DraftSessionListItem, ExportResult, InputArtifact, OutputDocument } from "../types/session";

const RAW_API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
const API_BASE_URL = RAW_API_BASE_URL.replace(/\/+$/, "");

function buildApiUrl(path: string): URL {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const origin =
    typeof window !== "undefined" && window.location?.origin ? window.location.origin : "http://localhost:8000";

  return new URL(`${API_BASE_URL}${normalizedPath}`, origin);
}

type BackendArtifact = {
  id: string;
  name: string;
  kind: InputArtifact["kind"];
  storage_path: string;
};

type BackendEvidenceReference = {
  id: string;
  artifact_id: string;
  kind: string;
  locator: string;
};

type BackendProcessStep = {
  id: string;
  step_number: number;
  application_name: string;
  action_text: string;
  source_data_note: string;
  timestamp: string;
  start_timestamp: string;
  end_timestamp: string;
  supporting_transcript_text: string;
  screenshot_id: string;
  confidence: ProcessStep["confidence"];
  evidence_references: BackendEvidenceReference[];
  screenshots: BackendStepScreenshot[];
  candidate_screenshots: BackendCandidateScreenshot[];
  edited_by_ba: boolean;
};

type BackendStepScreenshot = {
  id: string;
  artifact_id: string;
  role: string;
  sequence_number: number;
  timestamp: string;
  selection_method: string;
  is_primary: boolean;
  artifact: BackendArtifact;
};

type BackendCandidateScreenshot = {
  id: string;
  artifact_id: string;
  sequence_number: number;
  timestamp: string;
  source_role: string;
  selection_method: string;
  is_selected: boolean;
  artifact: BackendArtifact;
};

type BackendProcessNote = {
  id: string;
  text: string;
  related_step_ids: string[];
  evidence_reference_ids: string[];
  confidence: ProcessNote["confidence"];
  inference_type: string;
};

type BackendOutputDocument = {
  id: string;
  kind: string;
  storage_path: string;
  exported_at: string;
};

type BackendDraftSession = {
  id: string;
  title: string;
  status: DraftSession["status"];
  owner_id: string;
  diagram_type: DraftSession["diagramType"];
  artifacts: BackendArtifact[];
  process_steps: BackendProcessStep[];
  process_notes: BackendProcessNote[];
  output_documents: BackendOutputDocument[];
  action_logs: BackendActionLog[];
};

type BackendActionLog = {
  id: string;
  event_type: string;
  title: string;
  detail: string;
  actor: string;
  created_at: string;
};

type BackendDraftSessionListItem = {
  id: string;
  title: string;
  status: DraftSession["status"];
  owner_id: string;
  diagram_type: DraftSession["diagramType"];
  created_at: string;
  updated_at: string;
};

type BackendUser = {
  id: string;
  username: string;
  created_at: string;
};

type BackendAuthResponse = {
  token: string;
  user: BackendUser;
};

type CreateSessionPayload = {
  title: string;
  ownerId: string;
  diagramType: DraftSession["diagramType"];
};

type BackendDiagramNode = {
  id: string;
  label: string;
  category: DiagramModel["nodes"][number]["category"];
  step_range: string;
  width?: number;
  height?: number;
};

type BackendDiagramEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
  source_handle?: string;
  target_handle?: string;
};

type BackendDiagramModel = {
  diagram_type: DiagramModel["diagramType"];
  view_type: DiagramModel["viewType"];
  title: string;
  nodes: BackendDiagramNode[];
  edges: BackendDiagramEdge[];
};

type BackendDiagramLayoutResponse = {
  session_id: string;
  view_type: DiagramModel["viewType"];
  export_preset: DiagramExportPreset;
  canvas_settings: {
    theme: DiagramCanvasSettings["theme"];
    show_grid: boolean;
    grid_density: DiagramCanvasSettings["gridDensity"];
  };
  nodes: Array<{
    id: string;
    x: number;
    y: number;
    label?: string;
    width?: number;
    height?: number;
  }>;
};

type StepUpdatePayload = Partial<{
  applicationName: string;
  actionText: string;
  sourceDataNote: string;
  timestamp: string;
  startTimestamp: string;
  endTimestamp: string;
  supportingTranscriptText: string;
  screenshotId: string;
  confidence: ProcessStep["confidence"];
  editedByBa: boolean;
}>;

const AUTH_TOKEN_KEY = "pdd_generator_auth_token";

function mapArtifact(artifact: BackendArtifact): InputArtifact {
  return {
    id: artifact.id,
    name: artifact.name,
    kind: artifact.kind,
    storagePath: artifact.storage_path,
  };
}

function mapOutputDocument(output: BackendOutputDocument): OutputDocument {
  return {
    id: output.id,
    kind: output.kind === "pdf" ? "pdf" : "docx",
    storagePath: output.storage_path,
    exportedAt: output.exported_at,
  };
}

function mapProcessStep(step: BackendProcessStep): ProcessStep {
  return {
    id: step.id,
    stepNumber: step.step_number,
    applicationName: step.application_name,
    actionText: step.action_text,
    sourceDataNote: step.source_data_note,
    timestamp: step.timestamp,
    startTimestamp: step.start_timestamp,
    endTimestamp: step.end_timestamp,
    supportingTranscriptText: step.supporting_transcript_text,
    screenshotId: step.screenshot_id,
    confidence: step.confidence,
    evidenceReferences: step.evidence_references.map((reference) => ({
      id: reference.id,
      artifactId: reference.artifact_id,
      kind: reference.kind as ProcessStep["evidenceReferences"][number]["kind"],
      locator: reference.locator,
    })),
    screenshots: step.screenshots.map(mapStepScreenshot),
    candidateScreenshots: step.candidate_screenshots.map(mapCandidateScreenshot),
    editedByBa: step.edited_by_ba,
  };
}

function mapStepScreenshot(stepScreenshot: BackendStepScreenshot): StepScreenshot {
  return {
    id: stepScreenshot.id,
    artifactId: stepScreenshot.artifact_id,
    role: stepScreenshot.role,
    sequenceNumber: stepScreenshot.sequence_number,
    timestamp: stepScreenshot.timestamp,
    selectionMethod: stepScreenshot.selection_method,
    isPrimary: stepScreenshot.is_primary,
    artifact: {
      id: stepScreenshot.artifact.id,
      name: stepScreenshot.artifact.name,
      kind: "screenshot",
      storagePath: stepScreenshot.artifact.storage_path,
    },
  };
}

function mapCandidateScreenshot(candidateScreenshot: BackendCandidateScreenshot): CandidateScreenshot {
  return {
    id: candidateScreenshot.id,
    artifactId: candidateScreenshot.artifact_id,
    sequenceNumber: candidateScreenshot.sequence_number,
    timestamp: candidateScreenshot.timestamp,
    sourceRole: candidateScreenshot.source_role,
    selectionMethod: candidateScreenshot.selection_method,
    isSelected: candidateScreenshot.is_selected,
    artifact: {
      id: candidateScreenshot.artifact.id,
      name: candidateScreenshot.artifact.name,
      kind: "screenshot",
      storagePath: candidateScreenshot.artifact.storage_path,
    },
  };
}

function mapProcessNote(note: BackendProcessNote): ProcessNote {
  return {
    id: note.id,
    text: note.text,
    relatedStepIds: note.related_step_ids,
    evidenceReferenceIds: note.evidence_reference_ids,
    confidence: note.confidence,
    inferenceType: note.inference_type,
  };
}

function mapActionLog(actionLog: BackendActionLog): ActionLogEntry {
  return {
    id: actionLog.id,
    eventType: actionLog.event_type,
    title: actionLog.title,
    detail: actionLog.detail,
    actor: actionLog.actor,
    createdAt: actionLog.created_at,
  };
}

function mapDraftSession(session: BackendDraftSession): DraftSession {
  return {
    id: session.id,
    title: session.title,
    status: session.status,
    ownerId: session.owner_id,
    diagramType: session.diagram_type,
    inputArtifacts: session.artifacts.map(mapArtifact),
    processSteps: session.process_steps.map(mapProcessStep),
    processNotes: session.process_notes.map(mapProcessNote),
    outputDocuments: session.output_documents.map(mapOutputDocument),
    actionLogs: session.action_logs.map(mapActionLog),
  };
}

function mapDraftSessionListItem(session: BackendDraftSessionListItem): DraftSessionListItem {
  return {
    id: session.id,
    title: session.title,
    status: session.status,
    ownerId: session.owner_id,
    diagramType: session.diagram_type,
    createdAt: session.created_at,
    updatedAt: session.updated_at,
  };
}

function mapDiagramModel(diagram: BackendDiagramModel): DiagramModel {
  return {
    diagramType: diagram.diagram_type,
    viewType: diagram.view_type,
    title: diagram.title,
    nodes: diagram.nodes.map((node) => ({
      id: node.id,
      label: node.label,
      category: node.category,
      stepRange: node.step_range,
      width: node.width,
      height: node.height,
    })),
    edges: diagram.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      sourceHandle: edge.source_handle,
      targetHandle: edge.target_handle,
    })),
  };
}

function mapUser(user: BackendUser): User {
  return {
    id: user.id,
    username: user.username,
    createdAt: user.created_at,
  };
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const fallback = await response.text();
    throw new Error(fallback || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

function getDownloadFilename(response: Response, fallback: string): string {
  const contentDisposition = response.headers.get("content-disposition") ?? "";
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const quotedMatch = contentDisposition.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  return fallback;
}

export class ApiClient {
  private authToken = window.localStorage.getItem(AUTH_TOKEN_KEY) ?? "";

  setAuthToken(token: string): void {
    this.authToken = token;
    window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  }

  clearAuthToken(): void {
    this.authToken = "";
    window.localStorage.removeItem(AUTH_TOKEN_KEY);
  }

  private buildHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
    return this.authToken
      ? {
          Authorization: `Bearer ${this.authToken}`,
          ...extraHeaders,
        }
      : extraHeaders;
  }

  getArtifactContentUrl(artifactId: string): string {
    const url = buildApiUrl(`/uploads/artifacts/${artifactId}/content`);
    if (this.authToken) {
      url.searchParams.set("token", this.authToken);
    }
    return url.toString();
  }

  async register(username: string, password: string): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const payload = await parseJsonResponse<BackendAuthResponse>(response);
    this.setAuthToken(payload.token);
    return mapUser(payload.user);
  }

  async login(username: string, password: string): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const payload = await parseJsonResponse<BackendAuthResponse>(response);
    this.setAuthToken(payload.token);
    return mapUser(payload.user);
  }

  async logout(): Promise<void> {
    if (!this.authToken) {
      return;
    }
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      headers: this.buildHeaders(),
    });
    this.clearAuthToken();
  }

  async getCurrentUser(): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: this.buildHeaders(),
    });
    const user = await parseJsonResponse<BackendUser>(response);
    return mapUser(user);
  }

  async listDraftSessions(): Promise<DraftSessionListItem[]> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions`, {
      headers: this.buildHeaders(),
    });
    const sessions = await parseJsonResponse<BackendDraftSessionListItem[]>(response);
    return sessions.map(mapDraftSessionListItem);
  }

  async createDraftSession(payload: CreateSessionPayload): Promise<DraftSession> {
    const response = await fetch(`${API_BASE_URL}/uploads/sessions`, {
      method: "POST",
      headers: this.buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        title: payload.title,
        owner_id: payload.ownerId,
        diagram_type: payload.diagramType,
      }),
    });
    const session = await parseJsonResponse<BackendDraftSession>(response);
    return mapDraftSession(session);
  }

  async uploadArtifact(sessionId: string, artifactKind: InputArtifact["kind"], file: File): Promise<InputArtifact> {
    return this.uploadArtifactWithProgress(sessionId, artifactKind, file);
  }

  async uploadArtifactWithProgress(
    sessionId: string,
    artifactKind: InputArtifact["kind"],
    file: File,
    options?: { onProgress?: (progress: number) => void },
  ): Promise<InputArtifact> {
    const formData = new FormData();
    formData.append("artifact_kind", artifactKind);
    formData.append("file", file);

    return new Promise<InputArtifact>((resolve, reject) => {
      const request = new XMLHttpRequest();
      request.open("POST", `${API_BASE_URL}/uploads/sessions/${sessionId}/artifacts`);

      const headers = this.buildHeaders();
      Object.entries(headers).forEach(([key, value]) => {
        request.setRequestHeader(key, value);
      });

      request.upload.addEventListener("progress", (event) => {
        if (!options?.onProgress) {
          return;
        }
        if (event.lengthComputable) {
          options.onProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)));
          return;
        }
        options.onProgress(0);
      });

      request.addEventListener("load", () => {
        if (request.status < 200 || request.status >= 300) {
          reject(new Error(request.responseText || `Request failed with status ${request.status}`));
          return;
        }

        try {
          const artifact = JSON.parse(request.responseText) as BackendArtifact;
          options?.onProgress?.(100);
          resolve(mapArtifact(artifact));
        } catch (error) {
          reject(error instanceof Error ? error : new Error("Upload response could not be parsed."));
        }
      });

      request.addEventListener("error", () => {
        reject(new Error("Upload failed."));
      });

      request.addEventListener("abort", () => {
        reject(new Error("Upload aborted."));
      });

      request.send(formData);
    });
  }

  async generateDraftSession(sessionId: string): Promise<DraftSession> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/generate`, {
      method: "POST",
      headers: this.buildHeaders(),
    });
    const session = await parseJsonResponse<BackendDraftSession>(response);
    return mapDraftSession(session);
  }

  async getDraftSession(sessionId: string): Promise<DraftSession> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}`, {
      headers: this.buildHeaders(),
    });
    const session = await parseJsonResponse<BackendDraftSession>(response);
    return mapDraftSession(session);
  }

  async getDiagramModel(sessionId: string, viewType: DiagramModel["viewType"] = "overview"): Promise<DiagramModel> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/diagram-model?view=${viewType}`, {
      headers: this.buildHeaders(),
    });
    const diagram = await parseJsonResponse<BackendDiagramModel>(response);
    return mapDiagramModel(diagram);
  }

  async saveDiagramModel(sessionId: string, model: DiagramModel): Promise<DiagramModel> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/diagram-model?view=${model.viewType}`, {
      method: "PUT",
      headers: this.buildHeaders({ "Content-Type": "application/json" }),
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
    const diagram = await parseJsonResponse<BackendDiagramModel>(response);
    return mapDiagramModel(diagram);
  }

  async getDiagramLayout(
    sessionId: string,
    viewType: DiagramModel["viewType"] = "detailed",
  ): Promise<{ nodes: DiagramLayoutNodePosition[]; exportPreset: DiagramExportPreset; canvasSettings: DiagramCanvasSettings }> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/diagram-layout?view=${viewType}`, {
      headers: this.buildHeaders(),
    });
    const layout = await parseJsonResponse<BackendDiagramLayoutResponse>(response);
    return {
      nodes: layout.nodes,
      exportPreset: layout.export_preset,
      canvasSettings: {
        theme: layout.canvas_settings?.theme ?? "dark",
        showGrid: layout.canvas_settings?.show_grid ?? true,
        gridDensity: layout.canvas_settings?.grid_density ?? "medium",
      },
    };
  }

  async saveDiagramLayout(
    sessionId: string,
    nodes: DiagramLayoutNodePosition[],
    exportPreset: DiagramExportPreset,
    canvasSettings: DiagramCanvasSettings,
    viewType: DiagramModel["viewType"] = "detailed",
  ): Promise<{ nodes: DiagramLayoutNodePosition[]; exportPreset: DiagramExportPreset; canvasSettings: DiagramCanvasSettings }> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/diagram-layout?view=${viewType}`, {
      method: "PUT",
      headers: this.buildHeaders({ "Content-Type": "application/json" }),
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
    const layout = await parseJsonResponse<BackendDiagramLayoutResponse>(response);
    return {
      nodes: layout.nodes,
      exportPreset: layout.export_preset,
      canvasSettings: {
        theme: layout.canvas_settings?.theme ?? "dark",
        showGrid: layout.canvas_settings?.show_grid ?? true,
        gridDensity: layout.canvas_settings?.grid_density ?? "medium",
      },
    };
  }

  async saveDiagramArtifact(sessionId: string, imageDataUrl: string): Promise<DraftSession> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/diagram-artifact`, {
      method: "POST",
      headers: this.buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ image_data_url: imageDataUrl }),
    });
    const session = await parseJsonResponse<BackendDraftSession>(response);
    return mapDraftSession(session);
  }

  async updateProcessStep(sessionId: string, stepId: string, payload: StepUpdatePayload): Promise<ProcessStep> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/steps/${stepId}`, {
      method: "PATCH",
      headers: this.buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        application_name: payload.applicationName,
        action_text: payload.actionText,
        source_data_note: payload.sourceDataNote,
        timestamp: payload.timestamp,
        start_timestamp: payload.startTimestamp,
        end_timestamp: payload.endTimestamp,
        supporting_transcript_text: payload.supportingTranscriptText,
        screenshot_id: payload.screenshotId,
        confidence: payload.confidence,
        edited_by_ba: payload.editedByBa ?? true,
      }),
    });
    const step = await parseJsonResponse<BackendProcessStep>(response);
    return mapProcessStep(step);
  }

  async exportDocx(sessionId: string): Promise<ExportResult> {
    const response = await fetch(`${API_BASE_URL}/exports/${sessionId}/docx`, {
      method: "POST",
      headers: this.buildHeaders(),
    });
    const output = await parseJsonResponse<BackendOutputDocument>(response);
    return {
      id: output.id,
      kind: output.kind,
      storagePath: output.storage_path,
      exportedAt: output.exported_at,
    };
  }

  async downloadExportDocx(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/exports/${sessionId}/docx/download`, {
      method: "POST",
      headers: this.buildHeaders(),
    });

    if (!response.ok) {
      const fallback = await response.text();
      throw new Error(fallback || `Request failed with status ${response.status}`);
    }

    const blob = await response.blob();
    const filename = getDownloadFilename(response, `${sessionId}_draft.docx`);
    triggerBlobDownload(blob, filename);
  }

  async downloadExportPdf(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/exports/${sessionId}/pdf/download`, {
      method: "POST",
      headers: this.buildHeaders(),
    });

    if (!response.ok) {
      const fallback = await response.text();
      throw new Error(fallback || `Request failed with status ${response.status}`);
    }

    const blob = await response.blob();
    const filename = getDownloadFilename(response, `${sessionId}_draft.pdf`);
    triggerBlobDownload(blob, filename);
  }

  async updateStepScreenshot(
    sessionId: string,
    stepId: string,
    stepScreenshotId: string,
    payload: { isPrimary?: boolean; role?: string },
  ): Promise<ProcessStep> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/steps/${stepId}/screenshots/${stepScreenshotId}`, {
      method: "PATCH",
      headers: this.buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        is_primary: payload.isPrimary,
        role: payload.role,
      }),
    });
    const step = await parseJsonResponse<BackendProcessStep>(response);
    return mapProcessStep(step);
  }

  async deleteStepScreenshot(sessionId: string, stepId: string, stepScreenshotId: string): Promise<ProcessStep> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/steps/${stepId}/screenshots/${stepScreenshotId}`, {
      method: "DELETE",
      headers: this.buildHeaders(),
    });
    const step = await parseJsonResponse<BackendProcessStep>(response);
    return mapProcessStep(step);
  }

  async selectCandidateScreenshot(
    sessionId: string,
    stepId: string,
    candidateScreenshotId: string,
    payload: { isPrimary?: boolean; role?: string } = {},
  ): Promise<ProcessStep> {
    const response = await fetch(
      `${API_BASE_URL}/draft-sessions/${sessionId}/steps/${stepId}/candidate-screenshots/${candidateScreenshotId}/select`,
      {
        method: "POST",
        headers: this.buildHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          is_primary: payload.isPrimary,
          role: payload.role,
        }),
      },
    );
    const step = await parseJsonResponse<BackendProcessStep>(response);
    return mapProcessStep(step);
  }
}

export const apiClient = new ApiClient();
