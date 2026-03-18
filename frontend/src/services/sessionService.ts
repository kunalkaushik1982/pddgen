import type { ProcessStep } from "../types/process";
import type {
  DraftSession,
  DraftSessionListItem,
  SessionAnswer,
} from "../types/session";
import type {
  BackendDraftSession,
  BackendDraftSessionListItem,
  BackendProcessStep,
  BackendSessionAnswer,
  CreateSessionPayload,
  StepUpdatePayload,
} from "./contracts";
import { fetchJson } from "./http";
import { mapDraftSession, mapDraftSessionListItem, mapProcessStep, mapSessionAnswer } from "./mappers";

export const sessionService = {
  async listDraftSessions(): Promise<DraftSessionListItem[]> {
    const sessions = await fetchJson<BackendDraftSessionListItem[]>("/draft-sessions");
    return sessions.map(mapDraftSessionListItem);
  },

  async createDraftSession(payload: CreateSessionPayload): Promise<DraftSession> {
    const session = await fetchJson<BackendDraftSession>("/uploads/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: payload.title,
        owner_id: payload.ownerId,
        diagram_type: payload.diagramType,
      }),
    });
    return mapDraftSession(session);
  },

  async generateDraftSession(sessionId: string): Promise<DraftSession> {
    const session = await fetchJson<BackendDraftSession>(`/draft-sessions/${sessionId}/generate`, {
      method: "POST",
    });
    return mapDraftSession(session);
  },

  async getDraftSession(sessionId: string): Promise<DraftSession> {
    const session = await fetchJson<BackendDraftSession>(`/draft-sessions/${sessionId}`);
    return mapDraftSession(session);
  },

  async askSession(sessionId: string, question: string): Promise<SessionAnswer> {
    const answer = await fetchJson<BackendSessionAnswer>(`/draft-sessions/${sessionId}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    return mapSessionAnswer(answer);
  },

  async updateProcessStep(sessionId: string, stepId: string, payload: StepUpdatePayload): Promise<ProcessStep> {
    const step = await fetchJson<BackendProcessStep>(`/draft-sessions/${sessionId}/steps/${stepId}`, {
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
    return mapProcessStep(step);
  },

  async updateStepScreenshot(
    sessionId: string,
    stepId: string,
    stepScreenshotId: string,
    payload: { isPrimary?: boolean; role?: string },
  ): Promise<ProcessStep> {
    const step = await fetchJson<BackendProcessStep>(
      `/draft-sessions/${sessionId}/steps/${stepId}/screenshots/${stepScreenshotId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          is_primary: payload.isPrimary,
          role: payload.role,
        }),
      },
    );
    return mapProcessStep(step);
  },

  async deleteStepScreenshot(sessionId: string, stepId: string, stepScreenshotId: string): Promise<ProcessStep> {
    const step = await fetchJson<BackendProcessStep>(
      `/draft-sessions/${sessionId}/steps/${stepId}/screenshots/${stepScreenshotId}`,
      {
        method: "DELETE",
      },
    );
    return mapProcessStep(step);
  },

  async selectCandidateScreenshot(
    sessionId: string,
    stepId: string,
    candidateScreenshotId: string,
    payload: { isPrimary?: boolean; role?: string } = {},
  ): Promise<ProcessStep> {
    const step = await fetchJson<BackendProcessStep>(
      `/draft-sessions/${sessionId}/steps/${stepId}/candidate-screenshots/${candidateScreenshotId}/select`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          is_primary: payload.isPrimary,
          role: payload.role,
        }),
      },
    );
    return mapProcessStep(step);
  },
};
