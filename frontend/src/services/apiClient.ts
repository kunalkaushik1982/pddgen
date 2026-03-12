/**
 * Purpose: Typed frontend API client for upload, generation, review, and export.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\services\apiClient.ts
 */

import type { ProcessNote, ProcessStep, StepScreenshot } from "../types/process";
import type { DraftSession, ExportResult, InputArtifact, OutputDocument } from "../types/session";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

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
  artifacts: BackendArtifact[];
  process_steps: BackendProcessStep[];
  process_notes: BackendProcessNote[];
  output_documents: BackendOutputDocument[];
};

type CreateSessionPayload = {
  title: string;
  ownerId: string;
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
    kind: "docx",
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

function mapDraftSession(session: BackendDraftSession): DraftSession {
  return {
    id: session.id,
    title: session.title,
    status: session.status,
    ownerId: session.owner_id,
    inputArtifacts: session.artifacts.map(mapArtifact),
    processSteps: session.process_steps.map(mapProcessStep),
    processNotes: session.process_notes.map(mapProcessNote),
    outputDocuments: session.output_documents.map(mapOutputDocument),
  };
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const fallback = await response.text();
    throw new Error(fallback || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export class ApiClient {
  getArtifactContentUrl(artifactId: string): string {
    return `${API_BASE_URL}/uploads/artifacts/${artifactId}/content`;
  }

  async createDraftSession(payload: CreateSessionPayload): Promise<DraftSession> {
    const response = await fetch(`${API_BASE_URL}/uploads/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: payload.title,
        owner_id: payload.ownerId,
      }),
    });
    const session = await parseJsonResponse<BackendDraftSession>(response);
    return mapDraftSession(session);
  }

  async uploadArtifact(sessionId: string, artifactKind: InputArtifact["kind"], file: File): Promise<InputArtifact> {
    const formData = new FormData();
    formData.append("artifact_kind", artifactKind);
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/uploads/sessions/${sessionId}/artifacts`, {
      method: "POST",
      body: formData,
    });
    const artifact = await parseJsonResponse<BackendArtifact>(response);
    return mapArtifact(artifact);
  }

  async generateDraftSession(sessionId: string): Promise<DraftSession> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/generate`, {
      method: "POST",
    });
    const session = await parseJsonResponse<BackendDraftSession>(response);
    return mapDraftSession(session);
  }

  async getDraftSession(sessionId: string): Promise<DraftSession> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}`);
    const session = await parseJsonResponse<BackendDraftSession>(response);
    return mapDraftSession(session);
  }

  async updateProcessStep(sessionId: string, stepId: string, payload: StepUpdatePayload): Promise<ProcessStep> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/steps/${stepId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
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
    });
    const output = await parseJsonResponse<BackendOutputDocument>(response);
    return {
      id: output.id,
      kind: output.kind,
      storagePath: output.storage_path,
      exportedAt: output.exported_at,
    };
  }

  async updateStepScreenshot(
    sessionId: string,
    stepId: string,
    stepScreenshotId: string,
    payload: { isPrimary?: boolean; role?: string },
  ): Promise<ProcessStep> {
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/steps/${stepId}/screenshots/${stepScreenshotId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
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
    });
    const step = await parseJsonResponse<BackendProcessStep>(response);
    return mapProcessStep(step);
  }
}

export const apiClient = new ApiClient();
