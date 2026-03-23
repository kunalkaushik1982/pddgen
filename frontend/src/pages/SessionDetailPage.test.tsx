import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import { SessionDetailPage } from "./SessionDetailPage";
import type { DraftSession } from "../types/session";

vi.mock("./StepReviewPage", () => ({
  StepReviewPage: ({
    session,
    selectedStepId,
    initialReviewMode,
    headerActions,
  }: {
    session: DraftSession;
    selectedStepId: string | null;
    initialReviewMode?: "view" | "edit";
    headerActions?: React.ReactNode;
  }) => (
    <div>
      <div data-testid="step-review-page">
        {session.title}::{selectedStepId}::{initialReviewMode}
      </div>
      {headerActions}
    </div>
  ),
}));

function createSession(): DraftSession {
  return {
    id: "session-1",
    title: "Invoice Session",
    status: "review",
    ownerId: "kunal",
    diagramType: "flowchart",
    documentType: "pdd",
    hasUnprocessedEvidence: false,
    pendingEvidenceBundles: [],
    processGroups: [],
    inputArtifacts: [],
    processSteps: [
      {
        id: "step-1",
        stepNumber: 1,
        applicationName: "SAP",
        actionText: "Open invoice transaction",
        sourceDataNote: "",
        timestamp: "00:00:10",
        startTimestamp: "00:00:10",
        endTimestamp: "00:00:20",
        supportingTranscriptText: "Open invoice transaction",
        screenshotId: "",
        confidence: "high",
        evidenceReferences: [],
        screenshots: [],
        candidateScreenshots: [],
        editedByBa: false,
      },
    ],
    processNotes: [],
    outputDocuments: [],
    actionLogs: [],
  };
}

describe("SessionDetailPage", () => {
  it("renders an empty state when no session is loaded", () => {
    render(
      <SessionDetailPage
        session={null}
        selectedStepId={null}
        onExportDocx={vi.fn()}
        onExportPdf={vi.fn()}
        onSelectStep={vi.fn()}
        onSaveStep={vi.fn()}
        onSetPrimaryScreenshot={vi.fn()}
        onRemoveScreenshot={vi.fn()}
        onSelectCandidateScreenshot={vi.fn()}
      />,
    );

    expect(screen.getByText("No session is loaded.")).toBeInTheDocument();
  });

  it("renders the session review surface and wires header actions", async () => {
    const onExportDocx = vi.fn();
    const onExportPdf = vi.fn();

    render(
      <SessionDetailPage
        session={createSession()}
        selectedStepId="step-1"
        initialReviewMode="edit"
        onExportDocx={onExportDocx}
        onExportPdf={onExportPdf}
        onSelectStep={vi.fn()}
        onSaveStep={vi.fn()}
        onSetPrimaryScreenshot={vi.fn()}
        onRemoveScreenshot={vi.fn()}
        onRefreshSession={vi.fn()}
        onSelectCandidateScreenshot={vi.fn()}
      />,
    );

    expect(await screen.findByTestId("step-review-page")).toHaveTextContent("Invoice Session::step-1::edit");

    fireEvent.click(screen.getByRole("button", { name: "Word" }));
    fireEvent.click(screen.getByRole("button", { name: "PDF" }));

    expect(onExportDocx).toHaveBeenCalledTimes(1);
    expect(onExportPdf).toHaveBeenCalledTimes(1);
  });
});
