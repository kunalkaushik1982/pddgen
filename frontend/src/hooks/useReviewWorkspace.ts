import { useEffect, useState } from "react";

export type ReviewMode = "view" | "edit";
export type ViewWorkspaceTab = "summary" | "steps" | "diagram" | "ask" | "log";
export type EditWorkspaceTab = "steps" | "diagram";

type UseReviewWorkspaceOptions = {
  initialReviewMode: ReviewMode;
  sessionId: string | null;
};

export function useReviewWorkspace({ initialReviewMode, sessionId }: UseReviewWorkspaceOptions) {
  const [reviewMode, setReviewMode] = useState<ReviewMode>(initialReviewMode);
  const [activeViewTab, setActiveViewTab] = useState<ViewWorkspaceTab>("summary");
  const [activeEditTab, setActiveEditTab] = useState<EditWorkspaceTab>("steps");

  useEffect(() => {
    setReviewMode(initialReviewMode);
    setActiveViewTab("summary");
    setActiveEditTab("steps");
  }, [initialReviewMode, sessionId]);

  function switchMode(nextMode: ReviewMode) {
    setReviewMode(nextMode);
    if (nextMode === "edit") {
      setActiveEditTab(activeViewTab === "diagram" ? "diagram" : "steps");
      return;
    }

    if (activeEditTab === "diagram") {
      setActiveViewTab("diagram");
      return;
    }

    if (activeViewTab === "summary" || activeViewTab === "log") {
      setActiveViewTab(activeViewTab);
      return;
    }

    setActiveViewTab("steps");
  }

  return {
    reviewMode,
    activeViewTab,
    activeEditTab,
    setActiveViewTab,
    setActiveEditTab,
    switchMode,
  };
}
