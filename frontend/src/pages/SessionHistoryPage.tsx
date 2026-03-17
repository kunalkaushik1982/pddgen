/**
 * Purpose: List view of past user sessions with edit and export actions.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\SessionHistoryPage.tsx
 */

import React from "react";

import type { DraftSessionListItem } from "../types/session";

type SessionHistoryPageProps = {
  sessions: DraftSessionListItem[];
  disabled?: boolean;
  onOpenView: (sessionId: string) => void;
  onOpenEdit: (sessionId: string) => void;
  onRetry: (sessionId: string) => void;
  onExportDocx: (sessionId: string) => void;
  onExportPdf: (sessionId: string) => void;
};

export function SessionHistoryPage({
  sessions,
  disabled,
  onOpenView,
  onOpenEdit,
  onRetry,
  onExportDocx,
  onExportPdf,
}: SessionHistoryPageProps): JSX.Element {
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
                    <div className={`artifact-meta history-progress-label history-progress-label-${progressTone}`}>{progressLabel}</div>
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
            );
          })}
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

function getSessionProgress(tone: ReturnType<typeof getProgressTone>): number {
  switch (tone) {
    case "draft":
      return 20;
    case "queued":
      return 35;
    case "transcript":
      return 55;
    case "screenshots":
      return 72;
    case "diagram":
      return 88;
    case "ready":
    case "exported":
    case "failed":
      return 100;
    default:
      return 60;
  }
}

function getSessionProgressLabel(
  session: DraftSessionListItem,
  tone: ReturnType<typeof getProgressTone>,
): string {
  if (session.failureDetail) {
    return "Run failed";
  }

  switch (tone) {
    case "draft":
      return "Inputs uploaded";
    case "queued":
      return "Generation queued";
    case "transcript":
      return "Interpreting transcript";
    case "screenshots":
      return "Extracting screenshots";
    case "diagram":
      return "Building diagram";
    case "ready":
      return "Ready for review";
    case "exported":
      return "Export completed";
    case "failed":
      return "Run failed";
    default:
      return session.latestStageTitle || "Generation in progress";
  }
}

function getProgressTone(session: DraftSessionListItem): "draft" | "queued" | "screenshots" | "transcript" | "diagram" | "ready" | "exported" | "failed" {
  if (session.status === "failed" || session.failureDetail) {
    return "failed";
  }
  if (session.status === "exported") {
    return "exported";
  }

  const normalizedTitle = session.latestStageTitle.trim().toLowerCase();
  if (normalizedTitle === "ready for review" || session.status === "review") {
    return "ready";
  }
  if (normalizedTitle === "building diagram") {
    return "diagram";
  }
  if (normalizedTitle === "extracting screenshots") {
    return "screenshots";
  }
  if (normalizedTitle === "interpreting transcript") {
    return "transcript";
  }
  if (normalizedTitle === "generation queued") {
    return "queued";
  }
  return "draft";
}
