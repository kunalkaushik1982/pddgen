import React from "react";
import { render, screen } from "@testing-library/react";

import { StepReviewPage } from "./StepReviewPage";
import type { DraftSession } from "../types/session";

vi.mock("../components/review/ReviewWorkspaceTabs", () => ({
  ReviewWorkspaceTabs: () => <div data-testid="review-workspace-tabs" />,
}));

vi.mock("../components/review/SessionActionLogPanel", () => ({
  SessionActionLogPanel: () => <div data-testid="session-action-log-panel" />,
}));

vi.mock("../components/review/SessionArtifactsPanel", () => ({
  SessionArtifactsPanel: () => <div data-testid="session-artifacts-panel" />,
}));

vi.mock("../components/review/SessionDiagramSection", () => ({
  SessionDiagramSection: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("../components/review/SessionProcessSection", () => ({
  SessionProcessSection: () => <div data-testid="session-process-section" />,
}));

vi.mock("../components/review/SessionSummaryPanel", () => ({
  SessionSummaryPanel: () => <div data-testid="session-summary-panel" />,
}));

vi.mock("../hooks/useAskSession", () => ({
  useAskSession: () => ({
    isAsking: false,
    errorMessage: "",
    entries: [],
    selectedEvidence: null,
    selectCitation: vi.fn(),
    ask: vi.fn(),
  }),
}));

vi.mock("../hooks/useReviewWorkspace", () => ({
  useReviewWorkspace: () => ({
    reviewMode: "view",
    activeViewTab: "summary",
    activeEditTab: "steps",
    switchMode: vi.fn(),
    setActiveViewTab: vi.fn(),
    setActiveEditTab: vi.fn(),
  }),
}));

vi.mock("../hooks/useStepEditor", () => ({
  useStepEditor: () => ({
    draftValues: {},
    currentCandidate: null,
  }),
}));

function createSession(): DraftSession {
  return {
    id: "session-1",
    title: "Invoice Session",
    status: "review",
    ownerId: "owner-1",
    diagramType: "flowchart",
    documentType: "pdd",
    hasUnprocessedEvidence: false,
    pendingEvidenceBundles: [],
    processGroups: [
      {
        id: "group-1",
        sessionId: "session-1",
        title: "Legal Document Review And Analysis With Harvey Platform",
        canonicalSlug: "legal-document-review-and-analysis-with-harvey-platform",
        status: "active",
        summaryText: "",
        capabilityTags: [],
        displayOrder: 1,
        overviewDiagramJson: "",
        detailedDiagramJson: "",
      },
      {
        id: "group-2",
        sessionId: "session-1",
        title: "AI-Assisted Legal Document Analysis and Summarization with Co-Counsel",
        canonicalSlug: "ai-assisted-legal-document-analysis-and-summarization-with-co-counsel",
        status: "active",
        summaryText: "",
        capabilityTags: [],
        displayOrder: 2,
        overviewDiagramJson: "",
        detailedDiagramJson: "",
      },
    ],
    inputArtifacts: [],
    processSteps: [
      {
        id: "step-1",
        processGroupId: "group-1",
        stepNumber: 1,
        applicationName: "Harvey",
        actionText: "Open review",
        sourceDataNote: "",
        timestamp: "00:00:10",
        startTimestamp: "00:00:10",
        endTimestamp: "00:00:20",
        supportingTranscriptText: "Open review",
        screenshotId: "",
        confidence: "high",
        evidenceReferences: [],
        screenshots: [],
        candidateScreenshots: [],
        editedByBa: false,
      },
      {
        id: "step-2",
        processGroupId: "group-2",
        stepNumber: 2,
        applicationName: "Co-Counsel",
        actionText: "Summarize document",
        sourceDataNote: "",
        timestamp: "00:00:21",
        startTimestamp: "00:00:21",
        endTimestamp: "00:00:35",
        supportingTranscriptText: "Summarize document",
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

describe("StepReviewPage", () => {
  it("adds the full process title as a tooltip on detected process pills", () => {
    render(
      <StepReviewPage
        session={createSession()}
        selectedStepId="step-1"
        onSelectStep={vi.fn()}
        onSaveStep={vi.fn()}
        onSetPrimaryScreenshot={vi.fn()}
        onRemoveScreenshot={vi.fn()}
        onSelectCandidateScreenshot={vi.fn()}
      />,
    );

    const firstProcessPill = screen.getByRole("tab", {
      name: "Legal Document Review And Analysis With Harvey Platform",
    });

    expect(firstProcessPill).toHaveAttribute(
      "title",
      "Legal Document Review And Analysis With Harvey Platform",
    );
  });
});
