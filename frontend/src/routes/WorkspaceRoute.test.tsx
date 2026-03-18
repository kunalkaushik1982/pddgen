import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import { WorkspaceRoute } from "./WorkspaceRoute";

const mockUseWorkspaceFlow = vi.fn();
const mockUseAuth = vi.fn();

vi.mock("../hooks/useWorkspaceFlow", () => ({
  useWorkspaceFlow: () => mockUseWorkspaceFlow(),
}));

vi.mock("../providers/AuthProvider", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../pages/UploadPage", () => ({
  UploadPage: ({
    title,
    ownerId,
    uploadReady,
    actionBar,
  }: {
    title: string;
    ownerId: string;
    uploadReady?: boolean;
    actionBar?: React.ReactNode;
  }) => (
    <div data-testid="upload-page">
      <div>{title}</div>
      <div>{ownerId}</div>
      {uploadReady ? <div>Inputs uploaded</div> : null}
      {actionBar}
    </div>
  ),
}));

describe("WorkspaceRoute", () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: {
        id: "user-1",
        username: "kunal",
        createdAt: "2026-03-18T10:00:00Z",
      },
    });
  });

  it("hydrates the owner from the authenticated user and exposes workspace actions", () => {
    const uploadInputs = vi.fn();
    const generateDraft = vi.fn();
    const resumeDraft = vi.fn();
    const setOwnerId = vi.fn();

    mockUseWorkspaceFlow.mockReturnValue({
      title: "Invoice PDD",
      ownerId: "",
      diagramType: "flowchart",
      uploads: {
        videoFiles: [],
        transcriptFiles: [],
        templateFile: null,
        optionalArtifacts: {
          sopFiles: [],
          diagramFiles: [],
        },
      },
      uploadItems: [],
      canGenerateDraft: true,
      uploadPending: false,
      generatePending: false,
      canUploadInputs: true,
      isUploadingInputs: false,
      uploadInputs,
      generateDraft,
      setTitle: vi.fn(),
      setOwnerId,
      setDiagramType: vi.fn(),
      updateFiles: vi.fn(),
      resumableDraftSessions: [
        {
          id: "draft-1",
          title: "Uploaded Session",
          latestStageTitle: "Inputs uploaded",
          latestStageDetail: "Ready for generation.",
          updatedAt: "2026-03-18T11:00:00Z",
        },
      ],
      resumeDraft,
    });

    render(<WorkspaceRoute />);

    expect(setOwnerId).toHaveBeenCalledWith("kunal");

    fireEvent.click(screen.getByRole("button", { name: "Upload Inputs" }));
    fireEvent.click(screen.getByRole("button", { name: "Generate Draft" }));
    fireEvent.click(screen.getByRole("button", { name: "Continue Draft" }));

    expect(uploadInputs).toHaveBeenCalledTimes(1);
    expect(generateDraft).toHaveBeenCalledTimes(1);
    expect(resumeDraft).toHaveBeenCalledWith("draft-1");
  });

  it("does not reassign the owner when the workspace already matches the current user", () => {
    const setOwnerId = vi.fn();

    mockUseWorkspaceFlow.mockReturnValue({
      title: "Invoice PDD",
      ownerId: "kunal",
      diagramType: "flowchart",
      uploads: {
        videoFiles: [],
        transcriptFiles: [],
        templateFile: null,
        optionalArtifacts: {
          sopFiles: [],
          diagramFiles: [],
        },
      },
      uploadItems: [],
      canGenerateDraft: false,
      uploadPending: false,
      generatePending: false,
      canUploadInputs: false,
      isUploadingInputs: false,
      uploadInputs: vi.fn(),
      generateDraft: vi.fn(),
      setTitle: vi.fn(),
      setOwnerId,
      setDiagramType: vi.fn(),
      updateFiles: vi.fn(),
      resumableDraftSessions: [],
      resumeDraft: vi.fn(),
    });

    render(<WorkspaceRoute />);

    expect(setOwnerId).not.toHaveBeenCalled();
    expect(screen.queryByText("Ready To Generate")).not.toBeInTheDocument();
  });
});
