import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AppFrame } from "./AppFrame";

const mockUseAuth = vi.fn();
const mockUseToast = vi.fn();

vi.mock("../providers/AuthProvider", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../providers/ToastProvider", () => ({
  useToast: () => mockUseToast(),
}));

describe("AppFrame", () => {
  beforeEach(() => {
    mockUseToast.mockReturnValue({ message: null });
  });

  it("redirects admin-console-only users away from workspace routes", () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: "admin-1",
        username: "admin",
        email: "admin@example.com",
        createdAt: "2026-04-10T00:00:00Z",
        isAdmin: true,
        adminConsoleOnly: true,
      },
      isLoading: false,
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={["/workspace"]}>
        <Routes>
          <Route element={<AppFrame />}>
            <Route path="/workspace" element={<div>Workspace content</div>} />
            <Route path="/admin" element={<div>Admin content</div>} />
            <Route path="/about" element={<div>About content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.queryByText("Workspace content")).not.toBeInTheDocument();
    expect(screen.getByText("Admin content")).toBeInTheDocument();
  });
});
