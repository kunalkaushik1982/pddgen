import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { useToast } from "../providers/ToastProvider";
import { exportService } from "../services/exportService";
import { sessionService } from "../services/sessionService";
import type { ProcessStep } from "../types/process";
import { getErrorMessage } from "../utils/errors";

export function useSessionActions(sessionId: string | null, processSteps: ProcessStep[] = []) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);

  useEffect(() => {
    if (processSteps.length === 0) {
      setSelectedStepId(null);
      return;
    }
    setSelectedStepId((current) =>
      current && processSteps.some((step) => step.id === current) ? current : processSteps[0]?.id ?? null,
    );
  }, [processSteps]);

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
    onSuccess: async (_data, format) => {
      await refreshSession();
      showToast("info", `${format.toUpperCase()} downloaded.`);
    },
    onError: (error) => showToast("error", getErrorMessage(error)),
  });

  return {
    selectedStepId,
    setSelectedStepId,
    disabled:
      updateStepMutation.isPending ||
      setPrimaryScreenshotMutation.isPending ||
      removeScreenshotMutation.isPending ||
      selectCandidateMutation.isPending ||
      exportMutation.isPending,
    backToWorkspace: () => navigate("/workspace"),
    refreshSession,
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
