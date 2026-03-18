import type { ExportResult } from "../types/session";
import type { BackendOutputDocument } from "./contracts";
import { buildAuthHeaders, getDownloadFilename, parseJsonResponse, triggerBlobDownload, API_BASE_URL } from "./http";

export const exportService = {
  async exportDocx(sessionId: string): Promise<ExportResult> {
    const response = await fetch(`${API_BASE_URL}/exports/${sessionId}/docx`, {
      method: "POST",
      headers: buildAuthHeaders(),
    });
    const output = await parseJsonResponse<BackendOutputDocument>(response);
    return {
      id: output.id,
      kind: output.kind,
      storagePath: output.storage_path,
      exportedAt: output.exported_at,
    };
  },

  async downloadExportDocx(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/exports/${sessionId}/docx/download`, {
      method: "POST",
      headers: buildAuthHeaders(),
    });

    if (!response.ok) {
      const fallback = await response.text();
      throw new Error(fallback || `Request failed with status ${response.status}`);
    }

    const blob = await response.blob();
    const filename = getDownloadFilename(response, `${sessionId}_draft.docx`);
    triggerBlobDownload(blob, filename);
  },

  async downloadExportPdf(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/exports/${sessionId}/pdf/download`, {
      method: "POST",
      headers: buildAuthHeaders(),
    });

    if (!response.ok) {
      const fallback = await response.text();
      throw new Error(fallback || `Request failed with status ${response.status}`);
    }

    const blob = await response.blob();
    const filename = getDownloadFilename(response, `${sessionId}_draft.pdf`);
    triggerBlobDownload(blob, filename);
  },
};
