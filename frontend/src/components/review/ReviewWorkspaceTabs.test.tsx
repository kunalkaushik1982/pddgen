import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import { ReviewWorkspaceTabs } from "./ReviewWorkspaceTabs";

describe("ReviewWorkspaceTabs", () => {
  it("renders all view tabs and invokes the selected callback", () => {
    const onSelectViewTab = vi.fn();
    const onSelectEditTab = vi.fn();

    render(
      <ReviewWorkspaceTabs
        reviewMode="view"
        activeViewTab="summary"
        activeEditTab="steps"
        onSelectViewTab={onSelectViewTab}
        onSelectEditTab={onSelectEditTab}
      />,
    );

    fireEvent.click(screen.getByRole("tab", { name: "Ask" }));

    expect(onSelectViewTab).toHaveBeenCalledWith("ask");
    expect(onSelectEditTab).not.toHaveBeenCalled();
  });

  it("supports keyboard navigation across view tabs", () => {
    const onSelectViewTab = vi.fn();

    render(
      <ReviewWorkspaceTabs
        reviewMode="view"
        activeViewTab="summary"
        activeEditTab="steps"
        onSelectViewTab={onSelectViewTab}
        onSelectEditTab={vi.fn()}
      />,
    );

    fireEvent.keyDown(screen.getByRole("tab", { name: "Summary" }), { key: "ArrowRight" });
    fireEvent.keyDown(screen.getByRole("tab", { name: "Summary" }), { key: "End" });

    expect(onSelectViewTab).toHaveBeenNthCalledWith(1, "steps");
    expect(onSelectViewTab).toHaveBeenNthCalledWith(2, "log");
  });
});
