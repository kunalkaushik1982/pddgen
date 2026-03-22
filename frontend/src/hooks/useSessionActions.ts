import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { useToast } from "../providers/ToastProvider";
import { exportService } from "../services/exportService";
import { sessionService } from "../services/sessionService";
import type { ProcessStep } from "../types/process";
import type { DraftSessionListItem } from "../types/session";
import { getErrorMessage } from "../utils/errors";

export function useSessionActions(
  sessionId: string | null,
  processSteps: ProcessStep[] = [],
  sessionUpdatedAt: string | null = null,
  latestActionLogTitle: string | null = null,
) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<"docx" | "pdf" | null>(null);
  const [isGeneratingDraft, setIsGeneratingDraft] = useState(false);
  const [isGeneratingScreenshots, setIsGeneratingScreenshots] = useState(false);
  const [screenshotRefreshAnchor, setScreenshotRefreshAnchor] = useState<string | null>(null);
  const normalizedLatestActionTitle = (latestActionLogTitle ?? "").trim().toLowerCase();
  const screenshotStageActive = ["screenshot generation queued", "extracting screenshots"].includes(
    normalizedLatestActionTitle,
  );
  const draftStageActive = ["draft generation queued", "generation queued", "interpreting transcript", "building diagram"].includes(
    normalizedLatestActionTitle,
  );
  const draftActionLabel = processSteps.length > 0 ? "Regenerate Draft" : "Generate Draft";
  const hasExistingScreenshots = processSteps.some((step) => step.screenshots.length > 0);

  useEffect(() => {
    if (processSteps.length === 0) {
      setSelectedStepId(null);
      return;
    }
    setSelectedStepId((current) =>
      current && processSteps.some((step) => step.id === current) ? current : processSteps[0]?.id ?? null,
    );
  }, [processSteps]);

  useEffect(() => {
    if (!screenshotRefreshAnchor || !sessionUpdatedAt) {
      return;
    }
    if (sessionUpdatedAt !== screenshotRefreshAnchor) {
      setScreenshotRefreshAnchor(null);
      setIsGeneratingScreenshots(false);
    }
  }, [screenshotRefreshAnchor, sessionUpdatedAt]);

  useEffect(() => {
    if (screenshotStageActive) {
      setIsGeneratingScreenshots(true);
      return;
    }
    if (!screenshotRefreshAnchor) {
      setIsGeneratingScreenshots(false);
    }
  }, [screenshotRefreshAnchor, screenshotStageActive]);

  useEffect(() => {
    setIsGeneratingDraft(draftStageActive);
  }, [draftStageActive]);

  async function refreshSession(): Promise<void> {
    if (!sessionId) {
      return;
    }
    await queryClient.invalidateQueries({ queryKey: ["draftSession", sessionId] });
  }

  const updateStepMutation = useMutation({
    mutationFn: ({ stepId, payload }: { stepId: string; payload: Partial<ProcessStep> }) =>
      sessionService.updateProcessStep(sessionId!, stepId, payload),
    onSuccess: async () => {
      await refreshSession();
      showToast("info", "Step changes saved.");
    },
    onError: (error) => showToast("error", getErrorMessage(error)),
  });

  const setPrimaryScreenshotMutation = useMutation({
    mutationFn: ({ stepId, stepScreenshotId }: { stepId: string; stepScreenshotId: string }) =>
      sessionService.updateStepScreenshot(sessionId!, stepId, stepScreenshotId, { isPrimary: true }),
    onSuccess: async () => {
      await refreshSession();
      showToast("info", "Primary screenshot updated.");
    },
    onError: (error) => showToast("error", getErrorMessage(error)),
  });

  const removeScreenshotMutation = useMutation({
    mutationFn: ({ stepId, stepScreenshotId }: { stepId: string; stepScreenshotId: string }) =>
      sessionService.deleteStepScreenshot(sessionId!, stepId, stepScreenshotId),
    onSuccess: async () => {
      await refreshSession();
      showToast("info", "Screenshot removed from the step.");
    },
    onError: (error) => showToast("error", getErrorMessage(error)),
  });

  const selectCandidateMutation = useMutation({
    mutationFn: ({
      stepId,
      candidateScreenshotId,
      payload,
    }: {
      stepId: string;
      candidateScreenshotId: string;
      payload?: { isPrimary?: boolean; role?: string };
    }) => sessionService.selectCandidateScreenshot(sessionId!, stepId, candidateScreenshotId, payload),
    onSuccess: async () => {
      await refreshSession();
      showToast("info", "Screenshot selection updated.");
    },
    onError: (error) => showToast("error", getErrorMessage(error)),
  });

  const exportMutation = useMutation({
    mutationFn: async (format: "docx" | "pdf") => {
      if (!sessionId) {
        return;
      }
      if (format === "pdf") {
        await exportService.downloadExportPdf(sessionId);
        return;
      }
      await exportService.downloadExportDocx(sessionId);
    },
    onMutate: (format) => {
      setExportingFormat(format);
    },
    onSuccess: async (_data, format) => {
      await refreshSession();
      showToast("info", `${format.toUpperCase()} downloaded.`);
    },
    onError: (error) => showToast("error", getErrorMessage(error)),
    onSettled: () => {
      setExportingFormat(null);
    },
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      if (!sessionId) {
        return null;
      }
      return sessionService.generateDraftSession(sessionId);
    },
    onMutate: () => {
      setIsGeneratingDraft(true);
    },
    onSuccess: async (session) => {
      if (!sessionId || !session) {
        return;
      }
      queryClient.setQueryData<DraftSessionListItem[] | undefined>(["draftSessions"], (current) =>
        (current ?? []).map((item) =>
          item.id === sessionId
            ? {
                ...item,
                latestStageTitle: "Draft generation queued",
                latestStageDetail: "Transcript interpretation and canonical draft regeneration queued for this session.",
              }
            : item,
        ),
      );
      queryClient.setQueryData(["draftSession", sessionId], session);
      await queryClient.invalidateQueries({ queryKey: ["draftSession", sessionId] });
      await queryClient.invalidateQueries({ queryKey: ["draftSessions"] });
      showToast("info", "Draft generation started for this session.");
      navigate("/projects");
    },
    onError: (error) => showToast("error", getErrorMessage(error)),
    onSettled: () => {
      setIsGeneratingDraft(false);
    },
  });

  const screenshotMutation = useMutation({
    mutationFn: async () => {
      if (!sessionId) {
        return null;
      }
      return sessionService.generateSessionScreenshots(sessionId);
    },
    onMutate: () => {
      setIsGeneratingScreenshots(true);
    },
    onSuccess: async (session) => {
      if (!sessionId || !session) {
        return;
      }
      setScreenshotRefreshAnchor(sessionUpdatedAt);
      queryClient.setQueryData<DraftSessionListItem[] | undefined>(["draftSessions"], (current) =>
        (current ?? []).map((item) =>
          item.id === sessionId
            ? {
                ...item,
                latestStageTitle: "Screenshot generation queued",
                latestStageDetail: "Video-based screenshot derivation queued for the current canonical steps.",
              }
            : item,
        ),
      );
      queryClient.setQueryData(["draftSession", sessionId], session);
      await queryClient.invalidateQueries({ queryKey: ["draftSession", sessionId] });
      await queryClient.invalidateQueries({ queryKey: ["draftSessions"] });
      showToast("info", "Screenshot generation started for this session.");
      navigate("/projects");
    },
    onError: (error) => showToast("error", getErrorMessage(error)),
    onSettled: () => {
      if (!screenshotRefreshAnchor) {
        setIsGeneratingScreenshots(false);
      }
    },
  });

  return {
    selectedStepId,
    setSelectedStepId,
    exportingFormat,
    disabled:
      updateStepMutation.isPending ||
      setPrimaryScreenshotMutation.isPending ||
      removeScreenshotMutation.isPending ||
      selectCandidateMutation.isPending ||
      isGeneratingDraft ||
      isGeneratingScreenshots,
    generatingScreenshots: isGeneratingScreenshots,
    generatingDraft: isGeneratingDraft,
    draftActionLabel,
    backToWorkspace: () => navigate("/workspace"),
    refreshSession,
    generateDraft: () => generateMutation.mutate(),
    generateScreenshots: () => {
      if (hasExistingScreenshots) {
        const confirmed = window.confirm("Screenshots already exist for this session. Regenerate screenshots and replace the current set?");
        if (!confirmed) {
          return;
        }
      }
      screenshotMutation.mutate();
    },
    exportDocx: () => exportMutation.mutate("docx"),
    exportPdf: () => exportMutation.mutate("pdf"),
    saveStep: async (stepId: string, payload: Partial<ProcessStep>) => {
      await updateStepMutation.mutateAsync({ stepId, payload });
    },
    setPrimaryScreenshot: async (stepId: string, stepScreenshotId: string) => {
      await setPrimaryScreenshotMutation.mutateAsync({ stepId, stepScreenshotId });
    },
    removeScreenshot: async (stepId: string, stepScreenshotId: string) => {
      await removeScreenshotMutation.mutateAsync({ stepId, stepScreenshotId });
    },
    selectCandidateScreenshot: async (
      stepId: string,
      candidateScreenshotId: string,
      payload?: { isPrimary?: boolean; role?: string },
    ) => {
      await selectCandidateMutation.mutateAsync({ stepId, candidateScreenshotId, payload });
    },
  };
}
