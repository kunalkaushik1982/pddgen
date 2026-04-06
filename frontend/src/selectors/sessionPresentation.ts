import type { DraftSession, DraftSessionListItem } from "../types/session";

export type SessionProgressTone =
  | "draft"
  | "queued"
  | "screenshots"
  | "transcript"
  | "diagram"
  | "stalled"
  | "ready"
  | "exported"
  | "failed";

export function canOpenSession(status: DraftSessionListItem["status"]): boolean {
  return status === "review" || status === "exported" || status === "failed";
}

export function canExportSession(status: DraftSessionListItem["status"]): boolean {
  return status === "review" || status === "exported";
}

/** True if any step has selected and/or candidate screenshot rows from the API. */
export function sessionHasPersistedScreenshotEvidence(session: DraftSession): boolean {
  return session.processSteps.some(
    (step) => step.screenshots.length > 0 || step.candidateScreenshots.length > 0,
  );
}

export function isSessionActivelyProgressing(session: DraftSessionListItem): boolean {
  if (session.status === "processing") {
    return true;
  }

  const normalizedTitle = session.latestStageTitle.trim().toLowerCase();
  return [
    "draft generation queued",
    "generation queued",
    "interpreting transcript",
    "extracting screenshots",
    "building diagram",
    "screenshot generation queued",
  ].includes(normalizedTitle);
}

export function getProgressTone(session: DraftSessionListItem): SessionProgressTone {
  if (session.status === "failed") {
    return "failed";
  }
  if (session.status === "exported") {
    return "exported";
  }

  const normalizedTitle = session.latestStageTitle.trim().toLowerCase();
  if (normalizedTitle === "screenshots ready") {
    return "ready";
  }
  if (normalizedTitle === "building diagram") {
    return "diagram";
  }
  if (normalizedTitle === "screenshot run stalled" || normalizedTitle === "screenshot generation failed") {
    return "stalled";
  }
  if (normalizedTitle === "extracting screenshots") {
    return "screenshots";
  }
  if (normalizedTitle === "interpreting transcript") {
    return "transcript";
  }
  if (normalizedTitle === "generation queued" || normalizedTitle === "draft generation queued") {
    return "queued";
  }
  if (normalizedTitle === "screenshot generation queued") {
    return "screenshots";
  }
  if (normalizedTitle === "ready for review" || session.status === "review") {
    return "ready";
  }
  return "draft";
}

export function getSessionProgress(tone: SessionProgressTone): number {
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
    case "stalled":
      return 85;
    case "ready":
    case "exported":
    case "failed":
      return 100;
    default:
      return 60;
  }
}

export function getSessionProgressLabel(
  session: DraftSessionListItem,
  tone: SessionProgressTone,
): string {
  if (session.status === "failed" && session.failureDetail) {
    return "Run failed";
  }

  if (session.latestStageTitle.trim().toLowerCase() === "screenshots ready") {
    return "Screenshots ready";
  }

  switch (tone) {
    case "draft":
      return "Inputs uploaded";
    case "queued":
      return "Generation queued";
    case "transcript":
      return "Interpreting transcript";
    case "screenshots":
      return session.latestStageTitle || "Extracting screenshots";
    case "diagram":
      return "Building diagram";
    case "stalled":
      return session.latestStageTitle.trim() ? session.latestStageTitle : "Screenshot run stalled";
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
