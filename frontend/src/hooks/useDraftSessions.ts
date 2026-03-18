import { useQuery } from "@tanstack/react-query";

import { appConfig } from "../config/appConfig";
import { sessionService } from "../services/sessionService";

export function useDraftSessions() {
  return useQuery({
    queryKey: ["draftSessions"],
    queryFn: sessionService.listDraftSessions,
    refetchInterval: (query) =>
      query.state.data?.some((session) => session.status === "processing") ? appConfig.draftSessionPollingMs : false,
  });
}

export function useDraftSession(sessionId: string | null) {
  return useQuery({
    queryKey: ["draftSession", sessionId],
    queryFn: () => sessionService.getDraftSession(sessionId!),
    enabled: Boolean(sessionId),
    refetchInterval: (query) =>
      query.state.data?.status === "processing" ? appConfig.draftSessionPollingMs : false,
  });
}
