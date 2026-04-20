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
  const [includeDiagramInDraft, setIncludeDiagramInDraft] = useState(true);
  const draftSessionsQuery = useDraftSessions();

  const {
    title,
    ownerId,
    diagramType,
    documentType,
    uploads,
    uploadSessionId,
    uploadItems,
    setUploadSessionId,
    setUploadItems,
    hydrateFromDraftSession,
    removeSelectedFile: removeLocalSelectedFile,
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
    uploads.transcriptFiles.length > 0 && Boolean(uploads.templateFile);
  const hasUploadedDraftReady =
    Boolean(uploadSessionId) && uploadItems.length > 0 && uploadItems.every((item) => item.status === "uploaded");

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (uploadSessionId) {
        throw new Error("Inputs are already uploaded for this draft. Continue with Generate Draft.");
      }
      if (uploads.transcriptFiles.length === 0 || !uploads.templateFile) {
        throw new Error("At least one transcript and one template are required. Video is optional.");
      }

      const session = await sessionService.createDraftSession({ title, ownerId, diagramType, documentType });
      const queue = createArtifactQueue(uploads);
      const uploadBatchId = crypto.randomUUID();
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
          const uploadedArtifact = await uploadService.uploadArtifactWithProgress(
            session.id,
            item.artifactKind,
            item.file,
            {
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
            },
            undefined,
            uploadBatchId,
            item.uploadPairIndex ?? undefined,
          );
          setUploadItems((current) =>
            current.map((entry) =>
              entry.key === item.key
                ? {
                  ...entry,
                  artifactId: uploadedArtifact.id,
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
    mutationFn: async ({ sessionId, includeDiagram }: { sessionId: string; includeDiagram: boolean }) =>
      sessionService.generateDraftSession(sessionId, { includeDiagram }),
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

  const deleteDraftMutation = useMutation({
    mutationFn: async (sessionId: string) => sessionService.deleteDraftSession(sessionId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["draftSessions"] });
      showToast("info", "Draft removed from Workspace.");
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

  async function removeSelectedFile(
    field: "videoFiles" | "transcriptFiles" | "templateFile" | "sopFiles" | "diagramFiles",
    index: number,
  ): Promise<void> {
    const artifactKind =
      field === "videoFiles"
        ? "video"
        : field === "transcriptFiles"
          ? "transcript"
          : field === "templateFile"
            ? "template"
            : field === "sopFiles"
              ? "sop"
              : "diagram";
    const matchingItems = draftState.uploadItems.filter((item) => item.artifactKind === artifactKind);
    const targetItem = matchingItems[index] ?? null;

    if (uploadSessionId && targetItem?.artifactId && targetItem.status === "uploaded") {
      try {
        await uploadService.deleteUploadedArtifact(uploadSessionId, targetItem.artifactId);
        removeLocalSelectedFile(field, index);
        setUploadItems((current) => current.filter((item) => item.key !== targetItem.key));
        await queryClient.invalidateQueries({ queryKey: ["draftSessions"] });
        showToast("info", `${artifactKind === "template" ? "Template" : "Uploaded input"} removed.`);
        return;
      } catch (error) {
        showToast("error", getErrorMessage(error));
        return;
      }
    }

    removeLocalSelectedFile(field, index);
    if (targetItem) {
      setUploadItems((current) => current.filter((item) => item.key !== targetItem.key));
    }
  }

  async function deleteDraft(sessionId: string): Promise<void> {
    await deleteDraftMutation.mutateAsync(sessionId);
  }

  return {
    ...draftState,
    resumableDraftSessions,
    isUploadingInputs,
    canUploadInputs: requiredUploadSelected && !isUploadingInputs && !uploadSessionId,
    canGenerateDraft: hasUploadedDraftReady && !isUploadingInputs,
    uploadPending: uploadMutation.isPending,
    generatePending: generateMutation.isPending,
    deleteDraftPending: deleteDraftMutation.isPending,
    uploadInputs: () => {
      if (!uploadSessionId) {
        uploadMutation.mutate();
      }
    },
    generateDraft: () => {
      if (uploadSessionId) {
        generateMutation.mutate({ sessionId: uploadSessionId, includeDiagram: includeDiagramInDraft });
      }
    },
    includeDiagramInDraft,
    setIncludeDiagramInDraft,
    removeSelectedFile,
    resumeDraft,
    deleteDraft,
  };
}
