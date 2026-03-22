import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { DraftSession, InputArtifact } from "../../types/session";
import { meetingService } from "../../services/meetingService";
import { uploadService } from "../../services/uploadService";
import { useToast } from "../../providers/ToastProvider";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "An unexpected error occurred.";
}

export function MeetingsPanel({
  sessionId,
  session,
  disabled,
  onUpdateDraft,
  updatingDraft = false,
}: {
  sessionId: string;
  session: DraftSession | null;
  disabled?: boolean;
  onUpdateDraft?: () => void;
  updatingDraft?: boolean;
}): React.JSX.Element {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [transcriptFiles, setTranscriptFiles] = React.useState<File[]>([]);
  const [videoFiles, setVideoFiles] = React.useState<File[]>([]);
  const [uploadError, setUploadError] = React.useState<string | null>(null);
  const [hasPendingEvidenceUpdate, setHasPendingEvidenceUpdate] = React.useState(false);

  React.useEffect(() => {
    const latestTitle = session?.actionLogs?.[0]?.title?.trim().toLowerCase() ?? "";
    if (latestTitle === "ready for review" || latestTitle === "screenshots ready") {
      setHasPendingEvidenceUpdate(false);
    }
  }, [session?.actionLogs]);

  const uploadMutation = useMutation({
    mutationFn: async ({
      meetingId,
      kind,
      file,
      uploadBatchId,
      uploadPairIndex,
    }: {
      meetingId: string;
      kind: InputArtifact["kind"];
      file: File;
      uploadBatchId: string;
      uploadPairIndex: number;
    }) => uploadService.uploadArtifact(sessionId, kind, file, meetingId, uploadBatchId, uploadPairIndex),
    onSuccess: async () => {
      setUploadError(null);
      setHasPendingEvidenceUpdate(true);
      await queryClient.invalidateQueries({ queryKey: ["draftSession", sessionId] });
      await queryClient.invalidateQueries({ queryKey: ["draftSessions"] });
    },
    onError: (error) => {
      const message = getErrorMessage(error);
      setUploadError(message);
      showToast("error", message);
    },
  });

  async function uploadFiles(kind: InputArtifact["kind"], files: File[], uploadBatchId: string, meetingId: string): Promise<void> {
    for (const [index, file] of files.entries()) {
      await uploadMutation.mutateAsync({ meetingId, kind, file, uploadBatchId, uploadPairIndex: index });
    }
  }

  const isBusy = disabled || uploadMutation.isPending;
  const totalTranscripts = (session?.inputArtifacts ?? []).filter((artifact) => artifact.kind === "transcript").length;
  const totalVideos = (session?.inputArtifacts ?? []).filter((artifact) => artifact.kind === "video").length;

  return (
    <section className="panel stack meetings-panel meetings-panel-simple">
      <div className="meetings-upload-card">
        <div>
          <strong>Add New Recording</strong>
          <div className="artifact-meta">
            {`A new meeting will be created for this upload. Session evidence so far: ${totalTranscripts} transcript(s), ${totalVideos} video(s).`}
          </div>
        </div>

        <div className="meetings-evidence-row">
          <label className="app-user-menu-field meetings-field meetings-file-field">
            <span>Video</span>
            <input
              type="file"
              multiple
              disabled={isBusy}
              accept="video/*"
              onChange={(event) => setVideoFiles(Array.from(event.target.files ?? []))}
            />
          </label>
          <label className="app-user-menu-field meetings-field meetings-file-field">
            <span>Transcript</span>
            <input
              type="file"
              multiple
              disabled={isBusy}
              accept=".txt,.vtt,.docx"
              onChange={(event) => setTranscriptFiles(Array.from(event.target.files ?? []))}
            />
          </label>
          <button
            type="button"
            className="button-primary meetings-upload-button"
            disabled={isBusy || (transcriptFiles.length === 0 && videoFiles.length === 0)}
            onClick={() => void (async () => {
              try {
                const uploadBatchId =
                  typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
                    ? crypto.randomUUID()
                    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
                const newMeeting = await meetingService.createMeeting(sessionId);
                let uploadedCount = 0;
                if (videoFiles.length > 0) {
                  await uploadFiles("video", videoFiles, uploadBatchId, newMeeting.id);
                  uploadedCount += videoFiles.length;
                  setVideoFiles([]);
                }
                if (transcriptFiles.length > 0) {
                  await uploadFiles("transcript", transcriptFiles, uploadBatchId, newMeeting.id);
                  uploadedCount += transcriptFiles.length;
                  setTranscriptFiles([]);
                }
                if (uploadedCount > 0) {
                  await queryClient.invalidateQueries({ queryKey: ["meetings", sessionId] });
                  showToast("info", `${uploadedCount} file${uploadedCount === 1 ? "" : "s"} uploaded to ${newMeeting.title}.`);
                }
              } catch {
                // Mutation already handles the error toast.
              }
            })()}
          >
            Add Evidence
          </button>
        </div>

        <div className="meetings-selection-summary">
          <span>{videoFiles.length} video file(s) selected</span>
          <span>{transcriptFiles.length} transcript file(s) selected</span>
        </div>
      </div>

      {hasPendingEvidenceUpdate ? (
        <div className="upload-ready-banner">
          <strong>New evidence uploaded</strong>
          <div className="artifact-meta">Update the draft now to incorporate the newly added recording. Generate screenshots after the draft finishes.</div>
          <div>
            <button
              type="button"
              className="button-primary"
              disabled={disabled || updatingDraft || !onUpdateDraft}
              aria-busy={updatingDraft}
              onClick={onUpdateDraft}
            >
              {updatingDraft ? "Updating Draft..." : "Update Draft from New Evidence"}
            </button>
          </div>
        </div>
      ) : null}

      {uploadError ? <div className="empty-state">{uploadError}</div> : null}
    </section>
  );
}
