import { useEffect, useState } from "react";

import type { CandidateScreenshot, ProcessStep } from "../types/process";

export type UseStepEditorResult = ReturnType<typeof useStepEditor>;

export function useStepEditor(selectedStep: ProcessStep | null) {
  const [draftValues, setDraftValues] = useState<Partial<ProcessStep>>({});
  const [isEditing, setIsEditing] = useState(false);
  const [candidateIndex, setCandidateIndex] = useState(0);

  useEffect(() => {
    setDraftValues(
      selectedStep
        ? {
            actionText: selectedStep.actionText,
            sourceDataNote: selectedStep.sourceDataNote,
            confidence: selectedStep.confidence,
          }
        : {},
    );
    setIsEditing(false);
  }, [selectedStep]);

  useEffect(() => {
    setCandidateIndex(0);
  }, [selectedStep?.id]);

  const currentCandidate = selectedStep?.candidateScreenshots[candidateIndex] ?? null;

  function openEditor(step: ProcessStep, onSelectStep: (stepId: string) => void): void {
    onSelectStep(step.id);
    setIsEditing(true);
  }

  function closeEditor(): void {
    setIsEditing(false);
  }

  function previousCandidate(): void {
    if (!selectedStep) {
      return;
    }
    setCandidateIndex((current) => (current === 0 ? selectedStep.candidateScreenshots.length - 1 : current - 1));
  }

  function nextCandidate(): void {
    if (!selectedStep) {
      return;
    }
    setCandidateIndex((current) =>
      current === selectedStep.candidateScreenshots.length - 1 ? 0 : current + 1,
    );
  }

  async function addCandidateToStep(
    step: ProcessStep,
    candidate: CandidateScreenshot,
    makePrimary: boolean,
    onSelectCandidateScreenshot: (
      stepId: string,
      candidateScreenshotId: string,
      payload?: { isPrimary?: boolean; role?: string },
    ) => Promise<void>,
  ): Promise<void> {
    await onSelectCandidateScreenshot(step.id, candidate.id, { isPrimary: makePrimary });
  }

  async function makeCandidatePrimary(
    step: ProcessStep,
    candidate: CandidateScreenshot,
    onSelectCandidateScreenshot: (
      stepId: string,
      candidateScreenshotId: string,
      payload?: { isPrimary?: boolean; role?: string },
    ) => Promise<void>,
  ): Promise<void> {
    await onSelectCandidateScreenshot(step.id, candidate.id, { isPrimary: true });
  }

  return {
    draftValues,
    setDraftValues,
    isEditing,
    openEditor,
    closeEditor,
    candidateIndex,
    currentCandidate,
    previousCandidate,
    nextCandidate,
    addCandidateToStep,
    makeCandidatePrimary,
  };
}
