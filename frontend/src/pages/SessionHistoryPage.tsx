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
} from "../selectors/sessionPresentation";
import type { DraftSessionListItem } from "../types/session";

type SessionHistoryPageProps = {
  sessions: DraftSessionListItem[];
  disabled?: boolean;
  exportingSessionId?: string | null;
  exportingFormat?: "docx" | "pdf" | null;
  onOpenView: (sessionId: string) => void;
  onOpenEdit: (sessionId: string) => void;
  onRetry: (sessionId: string) => void;
  onExportDocx: (sessionId: string) => void;
  onExportPdf: (sessionId: string) => void;
};

export function SessionHistoryPage({
  sessions,
  disabled,
  exportingSessionId = null,
  exportingFormat = null,
  onOpenView,
  onOpenEdit,
  onRetry,
  onExportDocx,
  onExportPdf,
}: SessionHistoryPageProps): React.JSX.Element {
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
                <div className="button-row">
                  <button
                    type="button"
                    className="button-secondary"
                    disabled={disabled || !canOpenSession(session.status)}
                    onClick={() => onOpenView(session.id)}
                  >
                    View
                  </button>
                  <button
                    type="button"
                    className="button-primary"
                    disabled={disabled || !canOpenSession(session.status)}
                    onClick={() => onOpenEdit(session.id)}
                  >
                    Edit
                  </button>
                  {session.canRetry ? (
                    <button
                      type="button"
                      className="button-secondary"
                      disabled={disabled}
                      onClick={() => onRetry(session.id)}
                    >
                      Retry
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="button-secondary export-button"
                    disabled={disabled || !canExportSession(session.status) || isExportingThisSession}
                    aria-busy={isExportingThisSession && exportingFormat === "docx"}
                    onClick={() => onExportDocx(session.id)}
                  >
                    <span className="file-badge file-badge-docx" aria-hidden="true">W</span>
                    <span>{isExportingThisSession && exportingFormat === "docx" ? "Preparing Word..." : "Word"}</span>
                  </button>
                  <button
                    type="button"
                    className="button-secondary export-button"
                    disabled={disabled || !canExportSession(session.status) || isExportingThisSession}
                    aria-busy={isExportingThisSession && exportingFormat === "pdf"}
                    onClick={() => onExportPdf(session.id)}
                  >
                    <span className="file-badge file-badge-pdf" aria-hidden="true">P</span>
                    <span>{isExportingThisSession && exportingFormat === "pdf" ? "Preparing PDF..." : "PDF"}</span>
                  </button>
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
