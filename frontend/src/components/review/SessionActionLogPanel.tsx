import React from "react";

import type { ActionLogEntry } from "../../types/session";

export function SessionActionLogPanel({ entries }: { entries: ActionLogEntry[] }): React.JSX.Element {
  return (
    <section className="review-subsection panel stack" role="tabpanel" aria-label="Action log">
      <div>
        <h3>Action Log</h3>
        <div className="artifact-meta">Meaningful session events that affect the final PDD output.</div>
      </div>

      {entries.length > 0 ? (
        <div className="summary-document">
          <div className="summary-document-label">Session activity</div>
          <div className="summary-document-card action-log-document-card">
            <div className="summary-document-title">Review and export activity</div>
            <ul className="action-log-document-list">
              {entries.map((entry) => (
                <li key={entry.id} className="action-log-document-item">
                  <div className="action-log-document-title">{entry.title}</div>
                  <div className="action-log-document-detail">{entry.detail}</div>
                  <div className="artifact-meta">
                    {entry.actor} | {new Date(entry.createdAt).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <div className="empty-state">No session activity is available yet.</div>
      )}
    </section>
  );
}
