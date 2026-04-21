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
  const [tokenUsageOpen, setTokenUsageOpen] = React.useState(false);
  const [openTokenSection, setOpenTokenSection] = React.useState<"run" | "skill" | "model">("run");

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
  const tokenUsage = session.tokenUsage ?? {
    calls: 0,
    promptTokens: 0,
    completionTokens: 0,
    totalTokens: 0,
    byModel: [],
    bySkill: [],
    byRun: [],
  };
  const formatNumber = (value: number) => value.toLocaleString();
  const formatPercent = (value: number) => `${value.toFixed(1)}%`;
  const tokenTotalBase = tokenUsage.totalTokens > 0 ? tokenUsage.totalTokens : 1;

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
      <section className="panel token-usage-panel">
        <button
          type="button"
          className="token-usage-header token-usage-header-button"
          onClick={() => setTokenUsageOpen((current) => !current)}
          aria-expanded={tokenUsageOpen}
        >
          <span className="token-usage-header-title">
            <h3>Token Usage</h3>
            <span className="muted">Session transparency</span>
          </span>
          <span className={`token-usage-caret ${tokenUsageOpen ? "token-usage-caret-open" : ""}`} aria-hidden="true">
            ▶
          </span>
        </button>
        {tokenUsageOpen ? (
          <div className="token-usage-root">
            <div className="token-usage-total">
              <span>Total {formatNumber(tokenUsage.totalTokens)}</span>
              <span>Prompt {formatNumber(tokenUsage.promptTokens)}</span>
              <span>Completion {formatNumber(tokenUsage.completionTokens)}</span>
              <span>Calls {formatNumber(tokenUsage.calls)}</span>
            </div>
            <section className="token-usage-details">
              <button
                type="button"
                className="token-usage-section-button"
                onClick={() => setOpenTokenSection("run")}
                aria-expanded={openTokenSection === "run"}
              >
                <span>Run-wise split</span>
                <span className={`token-usage-caret ${openTokenSection === "run" ? "token-usage-caret-open" : ""}`} aria-hidden="true">▶</span>
              </button>
              {openTokenSection === "run" ? (
                <div className="token-usage-list">
                  {tokenUsage.byRun.length ? (
                    tokenUsage.byRun.map((run) => (
                      <div key={`run-${run.runNumber}`} className="token-usage-row">
                        <strong>Run {run.runNumber}</strong>
                        <span>
                          {formatNumber(run.totalTokens)} tok{" "}
                          <small className="token-usage-percent">({formatPercent((run.totalTokens / tokenTotalBase) * 100)})</small>
                        </span>
                        <span>Prompt {formatNumber(run.promptTokens)}</span>
                        <span>Completion {formatNumber(run.completionTokens)}</span>
                        <span>{formatNumber(run.calls)} calls</span>
                      </div>
                    ))
                  ) : (
                    <p className="muted">No queued runs found yet.</p>
                  )}
                </div>
              ) : null}
            </section>
            <section className="token-usage-details">
              <button
                type="button"
                className="token-usage-section-button"
                onClick={() => setOpenTokenSection("skill")}
                aria-expanded={openTokenSection === "skill"}
              >
                <span>Skill / stage split</span>
                <span className={`token-usage-caret ${openTokenSection === "skill" ? "token-usage-caret-open" : ""}`} aria-hidden="true">▶</span>
              </button>
              {openTokenSection === "skill" ? (
                <div className="token-usage-list">
                  {tokenUsage.bySkill.length ? (
                    tokenUsage.bySkill.map((bucket) => (
                      <div key={`skill-${bucket.key}`} className="token-usage-row">
                        <strong>{bucket.key}</strong>
                        <span>
                          {formatNumber(bucket.totalTokens)} tok{" "}
                          <small className="token-usage-percent">({formatPercent((bucket.totalTokens / tokenTotalBase) * 100)})</small>
                        </span>
                        <span>Prompt {formatNumber(bucket.promptTokens)}</span>
                        <span>Completion {formatNumber(bucket.completionTokens)}</span>
                        <span>{formatNumber(bucket.calls)} calls</span>
                      </div>
                    ))
                  ) : (
                    <p className="muted">No skill-level usage available.</p>
                  )}
                </div>
              ) : null}
            </section>
            <section className="token-usage-details">
              <button
                type="button"
                className="token-usage-section-button"
                onClick={() => setOpenTokenSection("model")}
                aria-expanded={openTokenSection === "model"}
              >
                <span>Model split</span>
                <span className={`token-usage-caret ${openTokenSection === "model" ? "token-usage-caret-open" : ""}`} aria-hidden="true">▶</span>
              </button>
              {openTokenSection === "model" ? (
                <div className="token-usage-list">
                  {tokenUsage.byModel.length ? (
                    tokenUsage.byModel.map((bucket) => (
                      <div key={`model-${bucket.key}`} className="token-usage-row">
                        <strong>{bucket.key}</strong>
                        <span>
                          {formatNumber(bucket.totalTokens)} tok{" "}
                          <small className="token-usage-percent">({formatPercent((bucket.totalTokens / tokenTotalBase) * 100)})</small>
                        </span>
                        <span>Prompt {formatNumber(bucket.promptTokens)}</span>
                        <span>Completion {formatNumber(bucket.completionTokens)}</span>
                        <span>{formatNumber(bucket.calls)} calls</span>
                      </div>
                    ))
                  ) : (
                    <p className="muted">No model-level usage available.</p>
                  )}
                </div>
              ) : null}
            </section>
          </div>
        ) : null}
      </section>
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
