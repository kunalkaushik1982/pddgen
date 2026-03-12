/**
 * Purpose: DOCX export and repository handoff status.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\ExportPage.tsx
 */

import React from "react";

import type { DraftSession, ExportResult } from "../types/session";

type ExportPageProps = {
  session: DraftSession | null;
  exportResult: ExportResult | null;
  disabled?: boolean;
  onExport: () => void;
};

export function ExportPage({ session, exportResult, disabled, onExport }: ExportPageProps): JSX.Element {
  return (
    <section className="panel stack">
      <div>
        <h2>4. Export PDD</h2>
        <p className="muted">Generate the editable DOCX once the step review is complete.</p>
      </div>

      {session ? (
        <>
          <div className="timeline-list">
            <div className="timeline-card">
              <strong>Ready to export</strong>
              <div className="artifact-meta">{session.processSteps.length} reviewed step(s)</div>
            </div>
            <div className="timeline-card">
              <strong>Existing outputs</strong>
              <div className="artifact-meta">{session.outputDocuments.length} document(s)</div>
            </div>
          </div>

          <div className="button-row">
            <button type="button" className="button-primary" onClick={onExport} disabled={disabled}>
              Export DOCX
            </button>
          </div>

          {exportResult ? (
            <div className="artifact-card">
              <strong>Latest export</strong>
              <div className="artifact-meta">{exportResult.storagePath}</div>
              <div className="artifact-meta">Exported at {exportResult.exportedAt}</div>
            </div>
          ) : null}
        </>
      ) : (
        <div className="empty-state">A draft session is required before export becomes available.</div>
      )}
    </section>
  );
}
