import { act, renderHook } from "@testing-library/react";

import { useReviewWorkspace } from "./useReviewWorkspace";

describe("useReviewWorkspace", () => {
  it("keeps diagram focus when switching from view to edit and back", () => {
    const { result } = renderHook(() =>
      useReviewWorkspace({
        initialReviewMode: "view",
        sessionId: "session-1",
      }),
    );

    act(() => {
      result.current.setActiveViewTab("diagram");
    });

    act(() => {
      result.current.switchMode("edit");
    });

    expect(result.current.reviewMode).toBe("edit");
    expect(result.current.activeEditTab).toBe("diagram");

    act(() => {
      result.current.switchMode("view");
    });

    expect(result.current.reviewMode).toBe("view");
    expect(result.current.activeViewTab).toBe("diagram");
  });
});
