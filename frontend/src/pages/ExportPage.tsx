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
  showHeader?: boolean;
  onExport: () => void;
};

export function ExportPage({ session, exportResult, disabled, showHeader = true, onExport }: ExportPageProps): React.JSX.Element {
  return (
    <section className="panel stack export-panel">
      {showHeader ? <h2>4. Export PDD</h2> : null}

      {session ? (
        <>
          <div className="button-row">
            <button type="button" className="button-primary" onClick={onExport} disabled={disabled}>
              Export DOCX
            </button>
          </div>

          {exportResult ? (
            <div className="artifact-card export-result-card">
              <strong>Latest export</strong>
              <div className="artifact-meta">{toRelativeExportPath(exportResult.storagePath)}</div>
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

function toRelativeExportPath(storagePath: string): string {
  const normalized = storagePath.replaceAll("/", "\\");
  const marker = "\\storage\\local\\";
  const markerIndex = normalized.toLowerCase().indexOf(marker);
  if (markerIndex >= 0) {
    return normalized.slice(markerIndex + marker.length);
  }
  return normalized.split("\\").slice(-3).join("\\");
}
