/**
 * Purpose: Human-readable labels for draft session diagram / document settings.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\utils\sessionDraftLabels.ts
 */

import type { DocumentType } from "../types/session";

export function formatDocumentTypeLabel(documentType: DocumentType | string): string {
  return String(documentType || "pdd")
    .trim()
    .toUpperCase();
}

export function formatDiagramTypeLabel(diagramType: string): string {
  const normalized = String(diagramType || "").trim().toLowerCase();
  if (normalized === "flowchart") {
    return "Flowchart";
  }
  if (normalized === "sequence") {
    return "Sequence";
  }
  return diagramType || "—";
}

/** Text for whether the last queued draft run included diagram generation. */
export function formatIncludeDiagramInDraft(include: unknown): string {
  if (include === true) {
    return "Yes — diagram included in draft generation";
  }
  if (include === false) {
    return "No — Include diagram in draft generation was unchecked";
  }
  return "—";
}
