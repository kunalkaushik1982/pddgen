import { afterEach, describe, expect, it, vi } from "vitest";

import { artifactService } from "./artifactService";

describe("artifactService.resolveArtifactUrl", () => {
  const originalOrigin = window.location.origin;

  afterEach(() => {
    vi.stubGlobal("location", { ...window.location, origin: originalOrigin });
  });

  it("resolves /api preview paths against page origin (production-style relative API base)", () => {
    vi.stubGlobal("location", { ...window.location, origin: "https://app.example.com" });
    const out = artifactService.resolveArtifactUrl("/api/uploads/artifacts/x/preview?sig=1");
    expect(out).toBe("https://app.example.com/api/uploads/artifacts/x/preview?sig=1");
  });

  it("passes through absolute http(s) URLs", () => {
    const absolute = "https://cdn.example.com/a.png";
    expect(artifactService.resolveArtifactUrl(absolute)).toBe(absolute);
  });
});
