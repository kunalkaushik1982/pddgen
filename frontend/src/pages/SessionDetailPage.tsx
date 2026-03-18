/**
 * Purpose: Dedicated working page for one session's review, edit, and export flows.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\SessionDetailPage.tsx
 */

import React, { Suspense, lazy } from "react";

import type { ProcessStep } from "../types/process";
import type { DraftSession } from "../types/session";

const StepReviewPage = lazy(async () => {
  const module = await import("./StepReviewPage");
  return { default: module.StepReviewPage };
});

type ReviewMode = "view" | "edit";

type SessionDetailPageProps = {
  session: DraftSession | null;
  selectedStepId: string | null;
  initialReviewMode?: ReviewMode;
  disabled?: boolean;
  exportingFormat?: "docx" | "pdf" | null;
  onBackToWorkspace: () => void;
  onExportDocx: () => void;
  onExportPdf: () => void;
  onSelectStep: (stepId: string) => void;
  onSaveStep: (stepId: string, payload: Partial<ProcessStep>) => Promise<void>;
  onSetPrimaryScreenshot: (stepId: string, stepScreenshotId: string) => Promise<void>;
  onRemoveScreenshot: (stepId: string, stepScreenshotId: string) => Promise<void>;
  onRefreshSession?: () => Promise<void> | void;
  onSelectCandidateScreenshot: (
    stepId: string,
    candidateScreenshotId: string,
    payload?: { isPrimary?: boolean; role?: string },
  ) => Promise<void>;
};

export function SessionDetailPage({
  session,
  selectedStepId,
  initialReviewMode = "view",
  disabled,
  exportingFormat = null,
  onBackToWorkspace,
  onExportDocx,
  onExportPdf,
  onSelectStep,
  onSaveStep,
  onSetPrimaryScreenshot,
  onRemoveScreenshot,
  onRefreshSession,
  onSelectCandidateScreenshot,
}: SessionDetailPageProps): React.JSX.Element {
  if (!session) {
    return (
      <section className="panel stack">
        <div className="section-header-inline">
          <div>
            <h2>Session Detail</h2>
            <p className="muted">Open a session from My Projects or create a new one from Workspace.</p>
          </div>
          <button type="button" className="button-secondary" onClick={onBackToWorkspace}>
            Back to Workspace
          </button>
        </div>
        <div className="empty-state">No session is loaded.</div>
      </section>
    );
  }

  return (
    <section className="stack">
      <Suspense
        fallback={
          <section className="panel">
            <div className="empty-state">Loading session detail...</div>
          </section>
        }
      >
        <StepReviewPage
          session={session}
          selectedStepId={selectedStepId}
          initialReviewMode={initialReviewMode}
          disabled={disabled}
          showHeader={false}
          headerActions={
            <div className="button-row">
              <button type="button" className="button-secondary" onClick={onBackToWorkspace} disabled={disabled}>
                Back to Workspace
              </button>
              <button
                type="button"
                className="button-secondary export-button"
                onClick={onExportDocx}
                disabled={disabled || exportingFormat !== null}
                aria-busy={exportingFormat === "docx"}
              >
                <span className="file-badge file-badge-docx" aria-hidden="true">W</span>
                <span>{exportingFormat === "docx" ? "Preparing Word..." : "Word"}</span>
              </button>
              <button
                type="button"
                className="button-secondary export-button"
                onClick={onExportPdf}
                disabled={disabled || exportingFormat !== null}
                aria-busy={exportingFormat === "pdf"}
              >
                <span className="file-badge file-badge-pdf" aria-hidden="true">P</span>
                <span>{exportingFormat === "pdf" ? "Preparing PDF..." : "PDF"}</span>
              </button>
            </div>
          }
          onSelectStep={onSelectStep}
          onSaveStep={onSaveStep}
          onSetPrimaryScreenshot={onSetPrimaryScreenshot}
          onRemoveScreenshot={onRemoveScreenshot}
          onRefreshSession={onRefreshSession}
          onSelectCandidateScreenshot={onSelectCandidateScreenshot}
        />
      </Suspense>
    </section>
  );
}
