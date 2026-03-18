import type { InputArtifact } from "../types/session";
import type { BackendArtifact } from "./contracts";
import { API_BASE_URL, buildAuthHeaders } from "./http";
import { mapArtifact } from "./mappers";

export const uploadService = {
  async uploadArtifact(sessionId: string, artifactKind: InputArtifact["kind"], file: File): Promise<InputArtifact> {
    return this.uploadArtifactWithProgress(sessionId, artifactKind, file);
  },

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

      const headers = buildAuthHeaders();
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
  },
};
