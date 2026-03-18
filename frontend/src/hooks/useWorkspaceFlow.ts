import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { uiCopy } from "../constants/uiCopy";
import { useDraftSessions } from "./useDraftSessions";
import { useToast } from "../providers/ToastProvider";
import {
  createArtifactQueue,
  createInitialUploadItems,
  useWorkspaceDraft,
} from "../providers/WorkspaceDraftProvider";
import { sessionService } from "../services/sessionService";
import { uploadService } from "../services/uploadService";
import { getErrorMessage } from "../utils/errors";

export function useWorkspaceFlow() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const draftState = useWorkspaceDraft();
  const [isUploadingInputs, setIsUploadingInputs] = useState(false);
  const draftSessionsQuery = useDraftSessions();

  const {
    title,
    ownerId,
    diagramType,
    uploads,
    uploadSessionId,
    uploadItems,
    setUploadSessionId,
    setUploadItems,
    hydrateFromDraftSession,
    reset,
  } = draftState;

  const resumableDraftSessions = useMemo(
    () =>
      (draftSessionsQuery.data ?? []).filter(
        (session) => session.status === "draft" && session.resumeReady && session.id !== uploadSessionId,
      ),
    [draftSessionsQuery.data, uploadSessionId],
  );

  const requiredUploadSelected =
    uploads.videoFiles.length > 0 && uploads.transcriptFiles.length > 0 && Boolean(uploads.templateFile);
  const hasUploadedDraftReady =
    Boolean(uploadSessionId) && uploadItems.length > 0 && uploadItems.every((item) => item.status === "uploaded");

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (uploads.videoFiles.length === 0 || uploads.transcriptFiles.length === 0 || !uploads.templateFile) {
        throw new Error("At least one video, one transcript, and one template are required.");
      }

      const session = await sessionService.createDraftSession({ title, ownerId, diagramType });
      const queue = createArtifactQueue(uploads);
      setUploadItems(createInitialUploadItems(uploads));

      for (const item of queue) {
        setUploadItems((current) =>
          current.map((entry) =>
            entry.key === item.key
              ? {
                  ...entry,
                  status: "uploading",
                  progress: 0,
                  error: null,
                }
              : entry,
          ),
        );
        try {
          await uploadService.uploadArtifactWithProgress(session.id, item.artifactKind, item.file, {
            onProgress: (progress) => {
              setUploadItems((current) =>
                current.map((entry) =>
                  entry.key === item.key
                    ? {
                        ...entry,
                        status: "uploading",
                        progress,
                        error: null,
                      }
                    : entry,
                ),
              );
            },
          });
          setUploadItems((current) =>
            current.map((entry) =>
              entry.key === item.key
                ? {
                    ...entry,
                    status: "uploaded",
                    progress: 100,
                    error: null,
                  }
                : entry,
            ),
          );
        } catch (error) {
          const message = getErrorMessage(error);
          setUploadItems((current) =>
            current.map((entry) =>
              entry.key === item.key
                ? {
                    ...entry,
                    status: "failed",
                    error: message,
                  }
                : entry,
            ),
          );
          throw error;
        }
      }

      const refreshed = await sessionService.getDraftSession(session.id);
      setUploadSessionId(session.id);
      return refreshed;
    },
    onMutate: () => {
      setIsUploadingInputs(true);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["draftSessions"] });
      showToast("info", uiCopy.uploadCompletedToast);
    },
    onError: (error) => {
      setUploadSessionId(null);
      showToast("error", getErrorMessage(error));
    },
    onSettled: () => {
      setIsUploadingInputs(false);
    },
  });

  const generateMutation = useMutation({
    mutationFn: async (sessionId: string) => sessionService.generateDraftSession(sessionId),
    onSuccess: async (session) => {
      setUploadSessionId(null);
      setUploadItems([]);
      reset();
      queryClient.setQueryData(["draftSession", session.id], session);
      await queryClient.invalidateQueries({ queryKey: ["draftSessions"] });
      showToast("info", uiCopy.generationStartedToast);
      navigate("/projects");
    },
    onError: (error) => {
      showToast("error", getErrorMessage(error));
    },
  });

  async function resumeDraft(sessionId: string): Promise<void> {
    try {
      const fullSession = await sessionService.getDraftSession(sessionId);
      hydrateFromDraftSession(fullSession);
      showToast("info", uiCopy.resumedDraftToast);
    } catch (error) {
      showToast("error", getErrorMessage(error));
    }
  }

  return {
    ...draftState,
    resumableDraftSessions,
    isUploadingInputs,
    canUploadInputs: requiredUploadSelected && !isUploadingInputs,
    canGenerateDraft: hasUploadedDraftReady && !isUploadingInputs,
    uploadPending: uploadMutation.isPending,
    generatePending: generateMutation.isPending,
    uploadInputs: () => uploadMutation.mutate(),
    generateDraft: () => {
      if (uploadSessionId) {
        generateMutation.mutate(uploadSessionId);
      }
    },
    resumeDraft,
  };
}
