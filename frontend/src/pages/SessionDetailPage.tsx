/**
 * Purpose: Dedicated working page for one session's review, edit, and export flows.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\SessionDetailPage.tsx
 */

import React from "react";

import { StepReviewPage } from "./StepReviewPage";
import type { ProcessStep } from "../types/process";
import type { DraftSession } from "../types/session";

type SessionDetailPageProps = {
  session: DraftSession | null;
  selectedStepId: string | null;
  disabled?: boolean;
  onBackToWorkspace: () => void;
  onRefresh: () => void;
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
  disabled,
  onBackToWorkspace,
  onRefresh,
  onExportDocx,
  onExportPdf,
  onSelectStep,
  onSaveStep,
  onSetPrimaryScreenshot,
  onRemoveScreenshot,
  onRefreshSession,
  onSelectCandidateScreenshot,
}: SessionDetailPageProps): JSX.Element {
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
      <StepReviewPage
        session={session}
        selectedStepId={selectedStepId}
        disabled={disabled}
        showHeader={false}
        headerActions={
          <div className="button-row">
            <button type="button" className="button-secondary" onClick={onBackToWorkspace} disabled={disabled}>
              Back to Workspace
            </button>
            <button type="button" className="button-secondary" onClick={onRefresh} disabled={disabled}>
              Refresh
            </button>
            <button type="button" className="button-secondary export-button" onClick={onExportDocx} disabled={disabled}>
              <span className="file-badge file-badge-docx">W</span>
              <span>Word</span>
            </button>
            <button type="button" className="button-secondary export-button" onClick={onExportPdf} disabled={disabled}>
              <span className="file-badge file-badge-pdf">P</span>
              <span>PDF</span>
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
    </section>
  );
}
