/**
 * Purpose: List view of past user sessions with edit and export actions.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\SessionHistoryPage.tsx
 */

import React from "react";

import type { DraftSessionListItem } from "../types/session";

type SessionHistoryPageProps = {
  sessions: DraftSessionListItem[];
  disabled?: boolean;
  onRefresh: () => void;
  onOpen: (sessionId: string) => void;
  onExportDocx: (sessionId: string) => void;
  onExportPdf: (sessionId: string) => void;
};

export function SessionHistoryPage({
  sessions,
  disabled,
  onRefresh,
  onOpen,
  onExportDocx,
  onExportPdf,
}: SessionHistoryPageProps): JSX.Element {
  return (
    <section className="panel stack">
      <div className="section-header-inline">
        <div>
          <h2>Past Runs</h2>
          <p className="muted">Edit any previous draft session or download the final Word or PDF when it is ready.</p>
        </div>
        <button type="button" className="button-secondary" disabled={disabled} onClick={onRefresh}>
          Refresh
        </button>
      </div>

      {sessions.length > 0 ? (
        <div className="history-list">
          {sessions.map((session) => (
            <div key={session.id} className="history-card">
              <div className="history-card-main">
                <strong>{session.title}</strong>
                <div className="artifact-meta">
                  {session.status} | updated {new Date(session.updatedAt).toLocaleString()}
                </div>
                <div className="artifact-meta">Session ID: {session.id}</div>
                <div className="history-progress">
                  <div className="history-progress-bar">
                    <div
                      className={`history-progress-fill history-progress-${session.status}`}
                      style={{ width: `${getSessionProgress(session.status)}%` }}
                    />
                  </div>
                  <div className="artifact-meta">{getSessionProgressLabel(session.status)}</div>
                </div>
              </div>
              <div className="button-row">
                <button
                  type="button"
                  className="button-primary"
                  disabled={disabled || !canOpenSession(session.status)}
                  onClick={() => onOpen(session.id)}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="button-secondary export-button"
                  disabled={disabled || !canExportSession(session.status)}
                  onClick={() => onExportDocx(session.id)}
                >
                  <span className="file-badge file-badge-docx">W</span>
                  <span>Word</span>
                </button>
                <button
                  type="button"
                  className="button-secondary export-button"
                  disabled={disabled || !canExportSession(session.status)}
                  onClick={() => onExportPdf(session.id)}
                >
                  <span className="file-badge file-badge-pdf">P</span>
                  <span>PDF</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">No started runs found yet. Upload-only drafts stay in Workspace until generation begins.</div>
      )}
    </section>
  );
}

function canOpenSession(status: DraftSessionListItem["status"]): boolean {
  return status === "review" || status === "exported" || status === "failed";
}

function canExportSession(status: DraftSessionListItem["status"]): boolean {
  return status === "review" || status === "exported";
}

function getSessionProgress(status: DraftSessionListItem["status"]): number {
  switch (status) {
    case "draft":
      return 20;
    case "processing":
      return 60;
    case "review":
      return 100;
    case "exported":
      return 100;
    case "failed":
      return 100;
    default:
      return 0;
  }
}

function getSessionProgressLabel(status: DraftSessionListItem["status"]): string {
  switch (status) {
    case "draft":
      return "Session created";
    case "processing":
      return "Generation in progress";
    case "review":
      return "Ready for review";
    case "exported":
      return "Export completed";
    case "failed":
      return "Run failed";
    default:
      return "Unknown state";
  }
}
