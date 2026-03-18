import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { uiCopy } from "../constants/uiCopy";
import { SessionHistoryPage } from "../pages/SessionHistoryPage";
import { useDraftSessions } from "../hooks/useDraftSessions";
import { exportService } from "../services/exportService";
import { sessionService } from "../services/sessionService";
import { useToast } from "../providers/ToastProvider";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "An unexpected error occurred.";
}

export function ProjectsRoute(): React.JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const draftSessionsQuery = useDraftSessions();
  const [exportingSessionId, setExportingSessionId] = React.useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = React.useState<"docx" | "pdf" | null>(null);

  const retryMutation = useMutation({
    mutationFn: (sessionId: string) => sessionService.generateDraftSession(sessionId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["draftSessions"] });
      showToast("info", uiCopy.retryStartedToast);
    },
    onError: (error) => showToast("error", getErrorMessage(error)),
  });

  const exportMutation = useMutation({
    mutationFn: async ({ sessionId, format }: { sessionId: string; format: "docx" | "pdf" }) => {
      if (format === "pdf") {
        await exportService.downloadExportPdf(sessionId);
        return;
      }
      await exportService.downloadExportDocx(sessionId);
    },
    onMutate: ({ sessionId, format }) => {
      setExportingSessionId(sessionId);
      setExportingFormat(format);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["draftSessions"] });
    },
    onError: (error) => showToast("error", getErrorMessage(error)),
    onSettled: () => {
      setExportingSessionId(null);
      setExportingFormat(null);
    },
  });

  const sessions = (draftSessionsQuery.data ?? []).filter((session) => session.status !== "draft");

  return (
    <SessionHistoryPage
      sessions={sessions}
      disabled={retryMutation.isPending}
      exportingSessionId={exportingSessionId}
      exportingFormat={exportingFormat}
      onOpenView={(sessionId) => navigate(`/session/${sessionId}?mode=view`)}
      onOpenEdit={(sessionId) => navigate(`/session/${sessionId}?mode=edit`)}
      onRetry={(sessionId) => retryMutation.mutate(sessionId)}
      onExportDocx={(sessionId) => exportMutation.mutate({ sessionId, format: "docx" })}
      onExportPdf={(sessionId) => exportMutation.mutate({ sessionId, format: "pdf" })}
    />
  );
}
