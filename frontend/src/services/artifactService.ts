import { API_BASE_URL, buildAuthHeaders } from "./http";

export const artifactService = {
  async fetchArtifactBlob(artifactId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/uploads/artifacts/${artifactId}/content`, {
      headers: buildAuthHeaders(),
    });

    if (!response.ok) {
      const fallback = await response.text();
      throw new Error(fallback || `Request failed with status ${response.status}`);
    }

    return response.blob();
  },
};
