import { describe, expect, it } from "vitest";

import { artifactService } from "./artifactService";

describe("artifactService.resolveArtifactUrl", () => {
  it("resolves /api preview paths against API base (see VITE_API_BASE_URL / appConfig fallback)", () => {
    const out = artifactService.resolveArtifactUrl("/api/uploads/artifacts/x/preview?sig=1");
    expect(out).toBe("http://localhost:8000/api/uploads/artifacts/x/preview?sig=1");
  });

  it("passes through absolute http(s) URLs", () => {
    const absolute = "https://cdn.example.com/a.png";
    expect(artifactService.resolveArtifactUrl(absolute)).toBe(absolute);
  });
});
