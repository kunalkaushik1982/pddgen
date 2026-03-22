import type { Meeting } from "../types/meeting";
import type { BackendMeeting } from "./contracts";
import { API_BASE_URL, buildAuthHeaders, buildSecurityHeaders, fetchJson } from "./http";
import { mapMeeting } from "./mappers";

export const meetingService = {
  async listMeetings(sessionId: string): Promise<Meeting[]> {
    const meetings = await fetchJson<BackendMeeting[]>(`/draft-sessions/${sessionId}/meetings`);
    return meetings.map(mapMeeting);
  },

  async createMeeting(sessionId: string, payload: { title?: string; meetingDate?: string | null } = {}): Promise<Meeting> {
    const meeting = await fetchJson<BackendMeeting>(`/draft-sessions/${sessionId}/meetings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: payload.title ?? "",
        meeting_date: payload.meetingDate ?? null,
      }),
    });
    return mapMeeting(meeting);
  },

  async updateMeeting(
    sessionId: string,
    meetingId: string,
    payload: { title?: string; meetingDate?: string | null } = {},
  ): Promise<Meeting> {
    const meeting = await fetchJson<BackendMeeting>(`/draft-sessions/${sessionId}/meetings/${meetingId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...(payload.title !== undefined ? { title: payload.title } : {}),
        ...(payload.meetingDate !== undefined ? { meeting_date: payload.meetingDate } : {}),
      }),
    });
    return mapMeeting(meeting);
  },

  async discardEvidenceBundle(sessionId: string, bundleId: string): Promise<void> {
    const headers = buildSecurityHeaders("DELETE", buildAuthHeaders());
    const response = await fetch(`${API_BASE_URL}/draft-sessions/${sessionId}/meetings/evidence-bundles/${bundleId}`, {
      method: "DELETE",
      headers,
      credentials: "include",
    });
    if (!response.ok) {
      const contentType = response.headers.get("content-type") ?? "";
      if (contentType.includes("application/json")) {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(payload.detail || `Request failed with status ${response.status}`);
      }
      throw new Error((await response.text()) || `Request failed with status ${response.status}`);
    }
  },

  async reorderMeetings(sessionId: string, meetingIds: string[]): Promise<Meeting[]> {
    const meetings = await fetchJson<BackendMeeting[]>(`/draft-sessions/${sessionId}/meetings/reorder`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ meeting_ids: meetingIds }),
    });
    return meetings.map(mapMeeting);
  },
};
