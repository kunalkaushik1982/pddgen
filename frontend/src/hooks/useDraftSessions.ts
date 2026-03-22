import { useQuery } from "@tanstack/react-query";

import { appConfig } from "../config/appConfig";
import { sessionService } from "../services/sessionService";

function isSessionActivelyProgressing(latestStageTitle: string | undefined, status: string | undefined): boolean {
  if (status === "processing") {
    return true;
  }

  const normalizedTitle = (latestStageTitle ?? "").trim().toLowerCase();
  return [
    "draft generation queued",
    "generation queued",
    "interpreting transcript",
    "extracting screenshots",
    "building diagram",
    "screenshot generation queued",
  ].includes(normalizedTitle);
}

export function useDraftSessions() {
  return useQuery({
    queryKey: ["draftSessions"],
    queryFn: sessionService.listDraftSessions,
    refetchInterval: (query) =>
      query.state.data?.some((session) => isSessionActivelyProgressing(session.latestStageTitle, session.status))
        ? appConfig.draftSessionPollingMs
        : false,
  });
}

export function useDraftSession(sessionId: string | null) {
  return useQuery({
    queryKey: ["draftSession", sessionId],
    queryFn: () => sessionService.getDraftSession(sessionId!),
    enabled: Boolean(sessionId),
    refetchInterval: (query) =>
      isSessionActivelyProgressing(
        query.state.data?.actionLogs?.[0]?.title,
        query.state.data?.status,
      )
        ? appConfig.draftSessionPollingMs
        : false,
  });
}
