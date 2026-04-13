import { API_BASE_URL, buildAuthHeaders } from "./http";

export const artifactService = {
  getArtifactContentUrl(artifactId: string): string {
    return `${API_BASE_URL}/uploads/artifacts/${artifactId}/content`;
  },

  /**
   * Turn API preview paths (e.g. `/api/uploads/artifacts/...`) into an absolute URL for `<img src>`.
   * Resolve against the **API** base (VITE_API_BASE_URL), not the SPA origin: in dev the app runs on
   * :5173 while the API is on :8000; using `window.location.origin` sent preview requests to Vite (404).
   * Same-origin production deployments still work when VITE_API_BASE_URL matches that host.
   */
  resolveArtifactUrl(url: string): string {
    const trimmed = url.trim();
    if (/^https?:\/\//i.test(trimmed)) {
      return trimmed;
    }
    const base = `${API_BASE_URL.replace(/\/+$/, "")}/`;
    const path = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
    return new URL(path, base).toString();
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
