import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { ConfirmDialog } from "../components/common/ConfirmDialog";
import { MeetingsPanel } from "../components/session/MeetingsPanel";
import { uiCopy } from "../constants/uiCopy";
import { useDraftSession, useDraftSessions } from "../hooks/useDraftSessions";
import { SessionHistoryPage } from "../pages/SessionHistoryPage";
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
  const [extendingSessionId, setExtendingSessionId] = React.useState<string | null>(null);
  const extendSessionQuery = useDraftSession(extendingSessionId);
  const [exportingSessionId, setExportingSessionId] = React.useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = React.useState<"docx" | "pdf" | null>(null);
  const [generatingScreenshotsSessionId, setGeneratingScreenshotsSessionId] = React.useState<string | null>(null);
  const [confirmScreenshotSessionId, setConfirmScreenshotSessionId] = React.useState<string | null>(null);

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

  const extendDraftMutation = useMutation({
    mutationFn: (sessionId: string) => sessionService.generateDraftSession(sessionId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["draftSessions"] });
      if (extendingSessionId) {
        await queryClient.invalidateQueries({ queryKey: ["draftSession", extendingSessionId] });
      }
      showToast("info", "Draft generation started for this session.");
      setExtendingSessionId(null);
    },
    onError: (error) => showToast("error", getErrorMessage(error)),
  });

  const screenshotMutation = useMutation({
    mutationFn: async (sessionId: string) => sessionService.generateSessionScreenshots(sessionId),
    onMutate: (sessionId) => {
      setGeneratingScreenshotsSessionId(sessionId);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["draftSessions"] });
      showToast("info", "Screenshot generation started for this session.");
    },
    onError: (error) => {
      showToast("error", getErrorMessage(error));
    },
    onSettled: () => {
      setGeneratingScreenshotsSessionId(null);
    },
  });

  const sessions = (draftSessionsQuery.data ?? []).filter((session) => session.status !== "draft");

  return (
    <>
      {confirmScreenshotSessionId ? (
        <ConfirmDialog
          title="Regenerate Screenshots?"
          description="Screenshots already exist for this session. Regenerating will replace the current screenshot set."
          confirmLabel="Generate Screenshots"
          tone="danger"
          busy={generatingScreenshotsSessionId === confirmScreenshotSessionId}
          onCancel={() => setConfirmScreenshotSessionId(null)}
          onConfirm={() => {
            const sessionId = confirmScreenshotSessionId;
            setConfirmScreenshotSessionId(null);
            screenshotMutation.mutate(sessionId);
          }}
        />
      ) : null}

      {extendingSessionId && extendSessionQuery.data ? (
        <div className="editor-overlay" role="dialog" aria-modal="true" aria-labelledby="projects-extend-session-title">
          <div className="editor-workspace extend-workspace">
            <div className="editor-workspace-header">
              <div>
                <h3 id="projects-extend-session-title">Extend Session</h3>
                <div className="artifact-meta">Add new evidence and update the draft for {extendSessionQuery.data.title}.</div>
              </div>
              <button type="button" className="button-secondary" onClick={() => setExtendingSessionId(null)}>
                Close
              </button>
            </div>
            <div className="extend-workspace-body">
              <MeetingsPanel
                sessionId={extendingSessionId}
                session={extendSessionQuery.data}
                disabled={extendSessionQuery.isLoading || retryMutation.isPending || extendDraftMutation.isPending}
                onUpdateDraft={() => extendDraftMutation.mutate(extendingSessionId)}
                updatingDraft={extendDraftMutation.isPending}
              />
            </div>
          </div>
        </div>
      ) : null}
      <SessionHistoryPage
        sessions={sessions}
        disabled={retryMutation.isPending}
        exportingSessionId={exportingSessionId}
        exportingFormat={exportingFormat}
        extendingSessionId={extendingSessionId}
        generatingScreenshotsSessionId={generatingScreenshotsSessionId}
        onOpenView={(sessionId) => navigate(`/session/${sessionId}?mode=view`)}
        onOpenEdit={(sessionId) => navigate(`/session/${sessionId}?mode=edit`)}
        onOpenExtend={(sessionId) => setExtendingSessionId(sessionId)}
        onGenerateScreenshots={async (sessionId) => {
          const session = await sessionService.getDraftSession(sessionId);
          const hasExistingScreenshots = session.processSteps.some((step) => step.screenshots.length > 0);
          if (hasExistingScreenshots) {
            setConfirmScreenshotSessionId(sessionId);
            return;
          }
          screenshotMutation.mutate(sessionId);
        }}
        onRetry={(sessionId) => retryMutation.mutate(sessionId)}
        onExportDocx={(sessionId) => exportMutation.mutate({ sessionId, format: "docx" })}
        onExportPdf={(sessionId) => exportMutation.mutate({ sessionId, format: "pdf" })}
      />
    </>
  );
}
