/**
 * Purpose: Dedicated working page for one session's review, edit, and export flows.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\SessionDetailPage.tsx
 */

import React, { Suspense, lazy } from "react";

import { ConfirmDialog } from "../components/common/ConfirmDialog";
import type { ReviewMode } from "../hooks/useReviewWorkspace";
import type { ProcessStep } from "../types/process";
import { sessionHasPersistedScreenshotEvidence } from "../selectors/sessionPresentation";
import type { DraftSession } from "../types/session";

const StepReviewPage = lazy(async () => {
  const module = await import("./StepReviewPage");
  return { default: module.StepReviewPage };
});

type SessionDetailPageProps = {
  session: DraftSession | null;
  selectedStepId: string | null;
  initialReviewMode?: ReviewMode;
  disabled?: boolean;
  generatingScreenshots?: boolean;
  exportingFormat?: "docx" | "pdf" | null;
  onGenerateScreenshots?: () => void;
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
  generatingScreenshots = false,
  exportingFormat = null,
  onGenerateScreenshots,
  onExportDocx,
  onExportPdf,
  onSelectStep,
  onSaveStep,
  onSetPrimaryScreenshot,
  onRemoveScreenshot,
  onRefreshSession,
  onSelectCandidateScreenshot,
}: SessionDetailPageProps): React.JSX.Element {
  const [exportMenuOpen, setExportMenuOpen] = React.useState(false);
  const exportMenuRef = React.useRef<HTMLDivElement | null>(null);
  const [confirmScreenshotsOpen, setConfirmScreenshotsOpen] = React.useState(false);

  React.useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!exportMenuRef.current?.contains(event.target as Node)) {
        setExportMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  if (!session) {
    return (
      <section className="panel stack">
        <div className="section-header-inline">
          <div>
            <h2>Session Detail</h2>
            <p className="muted">Open a session from My Projects or create a new one from Workspace.</p>
          </div>
        </div>
        <div className="empty-state">No session is loaded.</div>
      </section>
    );
  }

  const hasExistingScreenshots = sessionHasPersistedScreenshotEvidence(session);

  return (
    <section className="stack">
      {confirmScreenshotsOpen ? (
        <ConfirmDialog
          title="Regenerate Screenshots?"
          description="Screenshots already exist for this session. Regenerating will replace the current screenshot set."
          confirmLabel="Generate Screenshots"
          tone="danger"
          busy={generatingScreenshots}
          onCancel={() => setConfirmScreenshotsOpen(false)}
          onConfirm={() => {
            setConfirmScreenshotsOpen(false);
            onGenerateScreenshots?.();
          }}
        />
      ) : null}
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
            <div className="button-row review-header-action-slot">
              <button
                type="button"
                className="button-secondary session-screenshot-action"
                onClick={() => {
                  if (hasExistingScreenshots) {
                    setConfirmScreenshotsOpen(true);
                    return;
                  }
                  onGenerateScreenshots?.();
                }}
                disabled={disabled || !onGenerateScreenshots}
                aria-busy={generatingScreenshots}
              >
                {generatingScreenshots ? "Generating Screenshots..." : "Generate Screenshots"}
              </button>
              <div className="history-export-menu" ref={exportMenuRef}>
                <button
                  type="button"
                  className="button-secondary export-button"
                  disabled={disabled || exportingFormat !== null}
                  aria-busy={exportingFormat !== null}
                  aria-expanded={exportMenuOpen}
                  aria-haspopup="menu"
                  onClick={() => setExportMenuOpen((current) => !current)}
                >
                  {exportingFormat ? "Exporting..." : "Export"}
                </button>
                {exportMenuOpen ? (
                  <div className="history-export-dropdown" role="menu" aria-label={`Export ${session.title}`}>
                    <button
                      type="button"
                      className="history-export-item"
                      role="menuitem"
                      disabled={disabled || exportingFormat !== null}
                      onClick={() => {
                        setExportMenuOpen(false);
                        onExportDocx();
                      }}
                    >
                      <span className="file-badge file-badge-docx" aria-hidden="true">W</span>
                      <span>Word</span>
                    </button>
                    <button
                      type="button"
                      className="history-export-item"
                      role="menuitem"
                      disabled={disabled || exportingFormat !== null}
                      onClick={() => {
                        setExportMenuOpen(false);
                        onExportPdf();
                      }}
                    >
                      <span className="file-badge file-badge-pdf" aria-hidden="true">P</span>
                      <span>PDF</span>
                    </button>
                  </div>
                ) : null}
              </div>
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
