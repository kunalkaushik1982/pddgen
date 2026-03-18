import React from "react";

import { ProcessStepList } from "./ProcessStepList";
import { StepReviewPanel } from "./StepReviewPanel";
import { StepEditorDialog } from "./StepEditorDialog";
import type { UseStepEditorResult } from "../../hooks/useStepEditor";
import type { ProcessStep } from "../../types/process";

type SessionProcessSectionProps = {
  panelId: string;
  labelledBy: string;
  title: string;
  subtitle: string;
  mode: "view" | "edit";
  stepEditor: UseStepEditorResult;
  selectedStep: ProcessStep | null;
  steps: ProcessStep[];
  selectedStepId: string | null;
  disabled?: boolean;
  onSelectStep: (stepId: string) => void;
  onSaveStep: (event: React.FormEvent<HTMLFormElement>) => Promise<void>;
  onSetPrimaryScreenshot: (stepScreenshotId: string) => Promise<void>;
  onRemoveScreenshot: (stepScreenshotId: string) => Promise<void>;
  onSelectCandidateScreenshot: (
    step: ProcessStep,
    candidate: ProcessStep["candidateScreenshots"][number],
    makePrimary?: boolean,
  ) => Promise<void>;
};

export function SessionProcessSection({
  panelId,
  labelledBy,
  title,
  subtitle,
  mode,
  stepEditor,
  selectedStep,
  steps,
  selectedStepId,
  disabled,
  onSelectStep,
  onSaveStep,
  onSetPrimaryScreenshot,
  onRemoveScreenshot,
  onSelectCandidateScreenshot,
}: SessionProcessSectionProps): React.JSX.Element {
  const currentCandidate = stepEditor.currentCandidate;

  return (
    <section className="review-subsection panel stack" role="tabpanel" id={panelId} aria-labelledby={labelledBy}>
      <div>
        <h3>{title}</h3>
        <div className="artifact-meta">{subtitle}</div>
      </div>

      <div className="review-layout">
        <ProcessStepList
          steps={steps}
          selectedStepId={selectedStepId}
          isEditing={mode === "edit" ? stepEditor.isEditing : false}
          onSelectStep={onSelectStep}
        />

        <div className="review-detail-column">
          {selectedStep ? (
            <>
              <StepReviewPanel
                step={selectedStep}
                readOnly={mode === "view"}
                onEdit={mode === "edit" ? (step) => stepEditor.openEditor(step, onSelectStep) : undefined}
                onSetPrimaryScreenshot={mode === "edit" ? onSetPrimaryScreenshot : undefined}
                onRemoveScreenshot={mode === "edit" ? onRemoveScreenshot : undefined}
              />

              {mode === "edit" && stepEditor.isEditing ? (
                <StepEditorDialog
                  disabled={disabled}
                  draftValues={stepEditor.draftValues}
                  currentCandidate={currentCandidate}
                  candidateIndex={stepEditor.candidateIndex}
                  totalCandidates={selectedStep.candidateScreenshots.length}
                  step={selectedStep}
                  onClose={stepEditor.closeEditor}
                  onSubmit={onSaveStep}
                  onActionTextChange={(value) =>
                    stepEditor.setDraftValues((current) => ({ ...current, actionText: value }))}
                  onSourceDataNoteChange={(value) =>
                    stepEditor.setDraftValues((current) => ({ ...current, sourceDataNote: value }))}
                  onConfidenceChange={(value) =>
                    stepEditor.setDraftValues((current) => ({ ...current, confidence: value }))}
                  onPreviousCandidate={stepEditor.previousCandidate}
                  onNextCandidate={stepEditor.nextCandidate}
                  onAddCandidateToStep={(step, candidate, makePrimary) =>
                    stepEditor.addCandidateToStep(step, candidate, makePrimary, async () => {
                      await onSelectCandidateScreenshot(step, candidate, makePrimary);
                    })}
                  onMakeCandidatePrimary={(step, candidate) =>
                    stepEditor.makeCandidatePrimary(step, candidate, async () => {
                      await onSelectCandidateScreenshot(step, candidate, true);
                    })}
                />
              ) : null}
            </>
          ) : null}
        </div>
      </div>
    </section>
  );
}
