import type { InputArtifact } from "../types/session";
import type { BackendArtifact } from "./contracts";
import { API_BASE_URL, buildAuthHeaders } from "./http";
import { getCookieValue } from "./csrf";
import { mapArtifact } from "./mappers";

export const uploadService = {
  async uploadArtifact(
    sessionId: string,
    artifactKind: InputArtifact["kind"],
    file: File,
    meetingId?: string,
    uploadBatchId?: string,
    uploadPairIndex?: number,
  ): Promise<InputArtifact> {
    return this.uploadArtifactWithProgress(sessionId, artifactKind, file, undefined, meetingId, uploadBatchId, uploadPairIndex);
  },

  async uploadArtifactWithProgress(
    sessionId: string,
    artifactKind: InputArtifact["kind"],
    file: File,
    options?: { onProgress?: (progress: number) => void },
    meetingId?: string,
    uploadBatchId?: string,
    uploadPairIndex?: number,
  ): Promise<InputArtifact> {
    const formData = new FormData();
    formData.append("artifact_kind", artifactKind);
    if (meetingId) {
      formData.append("meeting_id", meetingId);
    }
    if (uploadBatchId) {
      formData.append("upload_batch_id", uploadBatchId);
    }
    if (typeof uploadPairIndex === "number") {
      formData.append("upload_pair_index", String(uploadPairIndex));
    }
    formData.append("file", file);

    return new Promise<InputArtifact>((resolve, reject) => {
      const request = new XMLHttpRequest();
      request.open("POST", `${API_BASE_URL}/uploads/sessions/${sessionId}/artifacts`);
      request.withCredentials = true;

      const headers = buildAuthHeaders();
      Object.entries(headers).forEach(([key, value]) => {
        request.setRequestHeader(key, value);
      });
      const csrfToken = getCookieValue("pdd_generator_csrf");
      if (csrfToken) {
        request.setRequestHeader("X-CSRF-Token", csrfToken);
      }

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
  },

  async deleteUploadedArtifact(sessionId: string, artifactId: string): Promise<void> {
    const csrfToken = getCookieValue("pdd_generator_csrf");
    const headers = buildAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/uploads/sessions/${sessionId}/artifacts/${artifactId}`, {
      method: "DELETE",
      credentials: "include",
      headers: {
        ...headers,
        ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
      },
    });
    if (!response.ok) {
      throw new Error((await response.text()) || `Request failed with status ${response.status}`);
    }
  },
};
