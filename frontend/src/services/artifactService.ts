import { appConfig } from "../config/appConfig";
import { API_BASE_URL, buildAuthHeaders } from "./http";

function pageOrigin(): string {
  return typeof window !== "undefined" && window.location?.origin ? window.location.origin : appConfig.apiOriginFallback;
}

export const artifactService = {
  getArtifactContentUrl(artifactId: string): string {
    return `${API_BASE_URL}/uploads/artifacts/${artifactId}/content`;
  },

  /**
   * Turn API preview paths (e.g. `/api/uploads/artifacts/...`) into an absolute URL for `<img src>`.
   * Must use a real origin as the base — `new URL(path, "/api/")` throws when the base is relative.
   */
  resolveArtifactUrl(url: string): string {
    const trimmed = url.trim();
    if (/^https?:\/\//i.test(trimmed)) {
      return trimmed;
    }
    return new URL(trimmed, `${pageOrigin()}/`).toString();
  },

  async fetchArtifactBlob(artifactId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/uploads/artifacts/${artifactId}/content`, {
      headers: buildAuthHeaders(),
      credentials: "include",
    });

    if (!response.ok) {
      const fallback = await response.text();
      throw new Error(fallback || `Request failed with status ${response.status}`);
    }

    return response.blob();
  },
};
