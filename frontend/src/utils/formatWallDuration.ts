/**
 * Human-readable labels for background job wall times from the API.
 */

export function formatWallDurationSeconds(totalSeconds: number | null | undefined): string | null {
  if (totalSeconds == null || !Number.isFinite(totalSeconds)) {
    return null;
  }
  const s = Math.max(0, Math.round(totalSeconds));
  if (s < 60) {
    return `${s}s`;
  }
  const m = Math.floor(s / 60);
  const r = s % 60;
  return r ? `${m}m ${r}s` : `${m}m`;
}

type GenerationTimingFields = {
  draftGenerationDurationSeconds?: number | null;
  screenshotGenerationDurationSeconds?: number | null;
};

/** Single-line summary for list/detail surfaces (e.g. "Draft: 2m 15s · Screenshots: 45s"). */
export function formatGenerationTimeSummary(session: GenerationTimingFields): string | null {
  const parts: string[] = [];
  const draft = formatWallDurationSeconds(session.draftGenerationDurationSeconds ?? undefined);
  if (draft) {
    parts.push(`Draft: ${draft}`);
  }
  const screenshots = formatWallDurationSeconds(session.screenshotGenerationDurationSeconds ?? undefined);
  if (screenshots) {
    parts.push(`Screenshots: ${screenshots}`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}
