import React from "react";
import { render, screen } from "@testing-library/react";

import { RouteErrorBoundary } from "./RouteErrorBoundary";

function Crash(): React.JSX.Element {
  throw new Error("boom");
}

describe("RouteErrorBoundary", () => {
  it("renders fallback content when a child throws", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(
      <RouteErrorBoundary areaLabel="Workspace">
        <Crash />
      </RouteErrorBoundary>,
    );

    expect(screen.getByRole("heading", { name: "Workspace Unavailable" })).toBeInTheDocument();
    expect(screen.getByText("boom")).toBeInTheDocument();

    consoleErrorSpy.mockRestore();
  });
});
