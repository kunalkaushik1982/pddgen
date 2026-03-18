/**
 * Purpose: Processing status and generation actions for the draft session.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\ProcessingPage.tsx
 */

import React from "react";

import type { DraftSession } from "../types/session";

type ProcessingPageProps = {
  session: DraftSession | null;
  disabled?: boolean;
  showHeader?: boolean;
  onGenerate: () => void;
  onRefresh: () => void;
};

export function ProcessingPage({ session, disabled, showHeader = true, onGenerate, onRefresh }: ProcessingPageProps): React.JSX.Element {
  return (
    <section className="panel stack">
      {showHeader ? (
        <div>
          <h2>2. Generate Draft</h2>
          <p className="muted">Trigger extraction after the required artifacts are uploaded.</p>
        </div>
      ) : null}

      {session ? (
        <>
          <div className="timeline-list">
            <div className="timeline-card">
              <strong>Session</strong>
              <div className="artifact-meta">
                {session.title} | {session.id}
              </div>
            </div>
            <div className="timeline-card">
              <strong>Artifacts uploaded</strong>
              <div className="artifact-meta">{session.inputArtifacts.length} artifact(s)</div>
            </div>
            <div className="timeline-card">
              <strong>Current status</strong>
              <div className="artifact-meta">{session.status}</div>
            </div>
          </div>

          <div className="button-row">
            <button type="button" className="button-primary" onClick={onGenerate} disabled={disabled}>
              Generate AS-IS draft
            </button>
            <button type="button" className="button-secondary" onClick={onRefresh} disabled={disabled}>
              Refresh session
            </button>
          </div>
        </>
      ) : (
        <div className="empty-state">Create a session first. Generation becomes available after upload completes.</div>
      )}
    </section>
  );
}
