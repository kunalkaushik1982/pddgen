import React from "react";
import { render, screen } from "@testing-library/react";

import { AuthenticatedArtifactImage } from "./AuthenticatedArtifactImage";

const { getArtifactContentUrl, resolveArtifactUrl } = vi.hoisted(() => ({
  getArtifactContentUrl: vi.fn((artifactId: string) => `http://localhost:8000/api/uploads/artifacts/${artifactId}/content`),
  resolveArtifactUrl: vi.fn((url: string) => `http://localhost:8000${url}`),
}));

vi.mock("../../services/artifactService", () => ({
  artifactService: {
    getArtifactContentUrl,
    resolveArtifactUrl,
    fetchArtifactBlob: vi.fn(),
  },
}));

describe("AuthenticatedArtifactImage", () => {
  beforeEach(() => {
    getArtifactContentUrl.mockClear();
    resolveArtifactUrl.mockClear();
  });

  it("renders screenshot previews from previewUrl", () => {
    render(
      <AuthenticatedArtifactImage
        artifactId="artifact-1"
        previewUrl="/api/uploads/artifacts/artifact-1/preview?expires=123&sig=ok"
        alt="Step screenshot"
      />,
    );

    const image = screen.getByAltText("Step screenshot");
    expect(resolveArtifactUrl).toHaveBeenCalledWith("/api/uploads/artifacts/artifact-1/preview?expires=123&sig=ok");
    expect(getArtifactContentUrl).not.toHaveBeenCalled();
    expect(image).toHaveAttribute("src", "http://localhost:8000/api/uploads/artifacts/artifact-1/preview?expires=123&sig=ok");
  });
});
