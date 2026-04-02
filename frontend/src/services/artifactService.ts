import { API_BASE_URL, buildAuthHeaders } from "./http";

export const artifactService = {
  getArtifactContentUrl(artifactId: string): string {
    return `${API_BASE_URL}/uploads/artifacts/${artifactId}/content`;
  },

  resolveArtifactUrl(url: string): string {
    return new URL(url, `${API_BASE_URL}/`).toString();
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
