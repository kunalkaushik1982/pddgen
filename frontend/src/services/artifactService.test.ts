import { describe, expect, it } from "vitest";

import { artifactService, resolveArtifactPreviewUrl } from "./artifactService";

describe("resolveArtifactPreviewUrl", () => {
  it("resolves against absolute API base (local dev split port)", () => {
    const out = resolveArtifactPreviewUrl(
      "/api/uploads/artifacts/x/preview?sig=1",
      "http://localhost:8000/api",
      "http://localhost:5173",
    );
    expect(out).toBe("http://localhost:8000/api/uploads/artifacts/x/preview?sig=1");
  });

  it("resolves against page origin when API base is relative (production Docker / nginx)", () => {
    const out = resolveArtifactPreviewUrl(
      "/api/uploads/artifacts/x/preview?sig=1",
      "/api",
      "https://pdd.pyopenclaw.online",
    );
    expect(out).toBe("https://pdd.pyopenclaw.online/api/uploads/artifacts/x/preview?sig=1");
  });

  it("passes through absolute http(s) URLs", () => {
    expect(resolveArtifactPreviewUrl("https://cdn.example.com/a.png", "/api", "https://app.example.com")).toBe(
      "https://cdn.example.com/a.png",
    );
  });
});

describe("artifactService.resolveArtifactUrl", () => {
  it("delegates with module API_BASE_URL (defaults to localhost API in tests)", () => {
    const out = artifactService.resolveArtifactUrl("/api/uploads/artifacts/x/preview?sig=1");
    expect(out).toBe("http://localhost:8000/api/uploads/artifacts/x/preview?sig=1");
  });
});
