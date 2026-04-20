/**
 * Purpose: List view of past user sessions with edit and export actions.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\SessionHistoryPage.tsx
 */

import React from "react";

import {
  canExportSession,
  canOpenSession,
  getProgressTone,
  getSessionProgress,
  getSessionProgressLabel,
  isSessionActivelyProgressing,
} from "../selectors/sessionPresentation";
import { formatGenerationTimeSummary } from "../utils/formatWallDuration";
import type { DraftSessionListItem } from "../types/session";

type SessionHistoryPageProps = {
  sessions: DraftSessionListItem[];
  disabled?: boolean;
  exportingSessionId?: string | null;
  exportingFormat?: "docx" | "pdf" | null;
  extendingSessionId?: string | null;
  generatingScreenshotsSessionId?: string | null;
  onOpenView: (sessionId: string) => void;
  onOpenEdit: (sessionId: string) => void;
  onOpenExtend: (sessionId: string) => void;
  onGenerateScreenshots: (sessionId: string) => void;
  onRetry: (sessionId: string) => void;
  onExportDocx: (sessionId: string) => void;
  onExportPdf: (sessionId: string) => void;
};

export function SessionHistoryPage({
  sessions,
  disabled,
  exportingSessionId = null,
  exportingFormat = null,
  extendingSessionId = null,
  generatingScreenshotsSessionId = null,
  onOpenView,
  onOpenEdit,
  onOpenExtend,
  onGenerateScreenshots,
  onRetry,
  onExportDocx,
  onExportPdf,
}: SessionHistoryPageProps): React.JSX.Element {
  const [openExportMenuSessionId, setOpenExportMenuSessionId] = React.useState<string | null>(null);
  const exportMenuRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!exportMenuRef.current?.contains(event.target as Node)) {
        setOpenExportMenuSessionId(null);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  return (
    <section className="panel stack">
      <div className="section-header-inline">
        <div>
          <h2>My Projects</h2>
          <p className="muted">Open previous sessions in view or edit mode and download the final Word or PDF when ready.</p>
        </div>
      </div>

      {sessions.length > 0 ? (
        <div className="history-list">
          {sessions.map((session) => {
            const progressTone = getProgressTone(session);
            const progressPercent = getSessionProgress(progressTone);
            const progressLabel = getSessionProgressLabel(session, progressTone);
            const isExportingThisSession = exportingSessionId === session.id;
            const isExtendingThisSession = extendingSessionId === session.id;
            const isGeneratingScreenshotsThisSession = generatingScreenshotsSessionId === session.id;
            const isProcessingThisSession = isSessionActivelyProgressing(session);
            const actionsDisabledForSession = Boolean(disabled || isProcessingThisSession);
            const generationSummary = formatGenerationTimeSummary(session);

            return (
              <div key={session.id} className="history-card">
                <div className="history-card-main">
                  <strong>{session.title}</strong>
                  <div className="artifact-meta">
                    {session.status} | updated {new Date(session.updatedAt).toLocaleString()}
                  </div>
                  <div className="artifact-meta">Session ID: {session.id}</div>
                  <div className={`artifact-meta history-stage-title history-stage-title-${progressTone}`}>{progressLabel}</div>
                  <div className="artifact-meta">{session.failureDetail || session.latestStageDetail}</div>
                  {generationSummary ? (
                    <div className="artifact-meta muted">Last run times: {generationSummary}</div>
                  ) : null}
                  <div className="artifact-meta muted">
                    Tokens: {session.totalTokensReported.toLocaleString()} (prompt {session.totalPromptTokens.toLocaleString()}
                    {" + "}completion {session.totalCompletionTokens.toLocaleString()}) | calls {session.llmCallCount}
                  </div>
                  <div className="history-progress">
                    <div className="history-progress-bar">
                      <div
                        className={`history-progress-fill history-progress-${progressTone}`}
                        style={{ width: `${progressPercent}%` }}
                      />
                    </div>
                    {progressTone === "ready" || progressTone === "failed" || progressTone === "exported" ? null : (
                      <div className={`artifact-meta history-progress-label history-progress-label-${progressTone}`}>
                        {progressLabel}
                      </div>
                    )}
                  </div>
                </div>
                <div className="button-row history-card-actions">
                  <div className="button-group">
                    <button
                      type="button"
                      className="button-secondary history-action-button"
                      disabled={actionsDisabledForSession || !canOpenSession(session.status)}
                      onClick={() => onOpenView(session.id)}
                    >
                      View
                    </button>
                    <button
                      type="button"
                      className="button-primary history-action-button"
                      disabled={actionsDisabledForSession || !canOpenSession(session.status)}
                      onClick={() => onOpenEdit(session.id)}
                    >
                      Edit
                    </button>
                  </div>
                  <div className="button-group">
                    <button
                      type="button"
                      className="button-secondary history-action-button"
                      disabled={actionsDisabledForSession || !canOpenSession(session.status)}
                      aria-pressed={isExtendingThisSession}
                      onClick={() => onOpenExtend(session.id)}
                    >
                      Extend
                    </button>
                    <button
                      type="button"
                      className="button-secondary history-action-button"
                      disabled={actionsDisabledForSession || !canOpenSession(session.status) || isGeneratingScreenshotsThisSession}
                      aria-busy={isGeneratingScreenshotsThisSession}
                      onClick={() => onGenerateScreenshots(session.id)}
                    >
                      {isGeneratingScreenshotsThisSession ? "Generating..." : "Generate SS"}
                    </button>
                  {session.canRetry ? (
                      <button
                        type="button"
                        className="button-secondary history-action-button"
                        disabled={actionsDisabledForSession}
                        onClick={() => onRetry(session.id)}
                      >
                      Retry
                    </button>
                  ) : null}
                  </div>
                  <div
                    className="history-export-menu"
                    ref={openExportMenuSessionId === session.id ? exportMenuRef : null}
                  >
                    <button
                      type="button"
                      className="button-secondary history-action-button history-action-button-export"
                      disabled={actionsDisabledForSession || !canExportSession(session.status) || isExportingThisSession}
                      aria-busy={isExportingThisSession}
                      aria-expanded={openExportMenuSessionId === session.id}
                      aria-haspopup="menu"
                      onClick={() =>
                        setOpenExportMenuSessionId((current) => (current === session.id ? null : session.id))
                      }
                    >
                      {isExportingThisSession ? "Exporting..." : "Export"}
                    </button>
                    {openExportMenuSessionId === session.id ? (
                      <div className="history-export-dropdown" role="menu" aria-label={`Export ${session.title}`}>
                        <button
                          type="button"
                          className="history-export-item"
                          role="menuitem"
                          disabled={isExportingThisSession}
                          onClick={() => {
                            setOpenExportMenuSessionId(null);
                            onExportDocx(session.id);
                          }}
                        >
                          <span className="file-badge file-badge-docx" aria-hidden="true">W</span>
                          <span>Word</span>
                        </button>
                        <button
                          type="button"
                          className="history-export-item"
                          role="menuitem"
                          disabled={isExportingThisSession}
                          onClick={() => {
                            setOpenExportMenuSessionId(null);
                            onExportPdf(session.id);
                          }}
                        >
                          <span className="file-badge file-badge-pdf" aria-hidden="true">P</span>
                          <span>PDF</span>
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="empty-state">No started runs found yet. Upload-only drafts stay in Workspace until generation begins.</div>
      )}
    </section>
  );
}
