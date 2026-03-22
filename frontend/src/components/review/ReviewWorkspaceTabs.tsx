import React from "react";

import type { EditWorkspaceTab, ReviewMode, ViewWorkspaceTab } from "../../hooks/useReviewWorkspace";

type ReviewWorkspaceTabsProps = {
  reviewMode: ReviewMode;
  activeViewTab: ViewWorkspaceTab;
  activeEditTab: EditWorkspaceTab;
  onSelectViewTab: (tab: ViewWorkspaceTab) => void;
  onSelectEditTab: (tab: EditWorkspaceTab) => void;
};

export function ReviewWorkspaceTabs({
  reviewMode,
  activeViewTab,
  activeEditTab,
  onSelectViewTab,
  onSelectEditTab,
}: ReviewWorkspaceTabsProps): React.JSX.Element {
  const tabRefs = React.useRef<Array<HTMLButtonElement | null>>([]);

  function handleKeyNavigation<T extends string>(
    event: React.KeyboardEvent<HTMLButtonElement>,
    tabs: readonly T[],
    currentValue: T,
    onSelect: (tab: T) => void,
  ) {
    const currentIndex = tabs.indexOf(currentValue);
    if (currentIndex === -1) {
      return;
    }

    let nextIndex: number | null = null;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      nextIndex = (currentIndex + 1) % tabs.length;
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = tabs.length - 1;
    }

    if (nextIndex === null) {
      return;
    }

    event.preventDefault();
    const nextValue = tabs[nextIndex];
    onSelect(nextValue);
    tabRefs.current[nextIndex]?.focus();
  }

  if (reviewMode === "view") {
    const viewTabs = ["summary", "steps", "diagram", "ask", "log"] as const;
    return (
      <div className="review-workspace-tabs" role="tablist" aria-label="View workspace">
        {[
          ["summary", "Summary"],
          ["steps", "Process"],
          ["diagram", "Diagram"],
          ["ask", "Ask"],
          ["log", "Action Log"],
        ].map(([value, label], index) => (
          <button
            key={value}
            ref={(element) => {
              tabRefs.current[index] = element;
            }}
            type="button"
            id={`review-view-tab-${value}`}
            role="tab"
            aria-selected={activeViewTab === value}
            aria-controls={`review-view-panel-${value}`}
            tabIndex={activeViewTab === value ? 0 : -1}
            className={`review-workspace-tab ${activeViewTab === value ? "review-workspace-tab-active" : ""}`}
            onClick={() => onSelectViewTab(value as ViewWorkspaceTab)}
            onKeyDown={(event) =>
              handleKeyNavigation(event, viewTabs, activeViewTab, (tab) => onSelectViewTab(tab as ViewWorkspaceTab))}
          >
            {label}
          </button>
        ))}
      </div>
    );
  }

  const editTabs = ["steps", "diagram", "meetings"] as const;
  return (
    <div className="review-workspace-tabs" role="tablist" aria-label="Edit workspace">
      {[
        ["steps", "Process"],
        ["diagram", "Diagram"],
        ["meetings", "Meetings"],
      ].map(([value, label], index) => (
        <button
          key={value}
          ref={(element) => {
            tabRefs.current[index] = element;
          }}
          type="button"
          id={`review-edit-tab-${value}`}
          role="tab"
          aria-selected={activeEditTab === value}
          aria-controls={`review-edit-panel-${value}`}
          tabIndex={activeEditTab === value ? 0 : -1}
          className={`review-workspace-tab ${activeEditTab === value ? "review-workspace-tab-active" : ""}`}
          onClick={() => onSelectEditTab(value as EditWorkspaceTab)}
          onKeyDown={(event) =>
            handleKeyNavigation(event, editTabs, activeEditTab, (tab) => onSelectEditTab(tab as EditWorkspaceTab))}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
