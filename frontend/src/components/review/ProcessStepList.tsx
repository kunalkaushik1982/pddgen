import React from "react";

import type { ProcessStep } from "../../types/process";

type ProcessStepListProps = {
  steps: ProcessStep[];
  selectedStepId: string | null;
  isEditing?: boolean;
  onSelectStep: (stepId: string) => void;
};

export function ProcessStepList({
  steps,
  selectedStepId,
  isEditing = false,
  onSelectStep,
}: ProcessStepListProps): React.JSX.Element {
  return (
    <div className={`step-list review-step-list ${isEditing ? "step-list-editing" : ""}`}>
      {steps.map((step) => (
        <button
          key={step.id}
          type="button"
          className={`button-secondary review-step-button ${selectedStepId === step.id ? "review-step-button-active" : ""}`}
          onClick={() => onSelectStep(step.id)}
        >
          Step {step.stepNumber}: {step.actionText.slice(0, 80)}
        </button>
      ))}
    </div>
  );
}
