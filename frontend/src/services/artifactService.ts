import { appConfig } from "../config/appConfig";
import { API_BASE_URL, buildAuthHeaders } from "./http";

function siteOrigin(): string {
  return typeof window !== "undefined" && window.location?.origin ? window.location.origin : appConfig.apiOriginFallback;
}

/**
 * Build an absolute URL for signed artifact previews and `<img src>`.
 * - Dev: `apiBaseUrl` is absolute (e.g. `http://localhost:8000/api`) — resolve against that host.
 * - Production: `apiBaseUrl` is often relative (`/api` from Vite) — `new URL(path, "/api/")` throws;
 *   resolve path against the **page origin** so nginx can proxy `/api` on the same host.
 */
export function resolveArtifactPreviewUrl(url: string, apiBaseUrl: string, origin: string): string {
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }
  const path = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  const baseUrl = apiBaseUrl.replace(/\/+$/, "");
  if (/^https?:\/\//i.test(baseUrl)) {
    return new URL(path, `${baseUrl}/`).toString();
  }
  return new URL(path, `${origin}/`).toString();
}

export const artifactService = {
  getArtifactContentUrl(artifactId: string): string {
    return `${API_BASE_URL}/uploads/artifacts/${artifactId}/content`;
  },

  resolveArtifactUrl(url: string): string {
    return resolveArtifactPreviewUrl(url, API_BASE_URL, siteOrigin());
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
