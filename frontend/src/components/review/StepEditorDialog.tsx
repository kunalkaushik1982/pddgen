import React from "react";

import { AuthenticatedArtifactImage } from "../common/AuthenticatedArtifactImage";
import type { CandidateScreenshot, ProcessStep } from "../../types/process";

type StepEditorDialogProps = {
  disabled?: boolean;
  draftValues: Partial<ProcessStep>;
  currentCandidate: CandidateScreenshot | null;
  candidateIndex: number;
  totalCandidates: number;
  step: ProcessStep;
  onClose: () => void;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => Promise<void>;
  onActionTextChange: (value: string) => void;
  onSourceDataNoteChange: (value: string) => void;
  onConfidenceChange: (value: ProcessStep["confidence"]) => void;
  onPreviousCandidate: () => void;
  onNextCandidate: () => void;
  onAddCandidateToStep: (step: ProcessStep, candidate: CandidateScreenshot, makePrimary: boolean) => Promise<void>;
  onMakeCandidatePrimary: (step: ProcessStep, candidate: CandidateScreenshot) => Promise<void>;
};

export function StepEditorDialog({
  disabled,
  draftValues,
  currentCandidate,
  candidateIndex,
  totalCandidates,
  step,
  onClose,
  onSubmit,
  onActionTextChange,
  onSourceDataNoteChange,
  onConfidenceChange,
  onPreviousCandidate,
  onNextCandidate,
  onAddCandidateToStep,
  onMakeCandidatePrimary,
}: StepEditorDialogProps): React.JSX.Element {
  const actionTextRef = React.useRef<HTMLTextAreaElement | null>(null);
  const dialogBodyRef = React.useRef<HTMLDivElement | null>(null);
  const dialogTitleId = React.useId();
  const dialogDescriptionId = React.useId();

  React.useEffect(() => {
    actionTextRef.current?.focus();
  }, []);

  React.useEffect(() => {
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab" || !dialogBodyRef.current) {
        return;
      }

      const focusableElements = Array.from(
        dialogBodyRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), textarea:not([disabled]), select:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((element) => !element.hasAttribute("disabled") && element.tabIndex !== -1);

      if (focusableElements.length === 0) {
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey && activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <div className="editor-overlay" role="dialog" aria-modal="true" aria-labelledby={dialogTitleId} aria-describedby={dialogDescriptionId}>
      <div className="editor-workspace" ref={dialogBodyRef}>
        <div className="editor-workspace-header">
          <div>
            <h3 id={dialogTitleId}>Edit Step {step.stepNumber}</h3>
            <div className="artifact-meta" id={dialogDescriptionId}>
              {step.applicationName || "Application pending"} | {step.timestamp || "No timestamp"}
            </div>
          </div>
          <button type="button" className="button-secondary" onClick={onClose} disabled={disabled}>
            Close editor
          </button>
        </div>

        <div className="editor-workspace-grid">
          <div className="editor-visual-column">
            {currentCandidate ? (
              <div className="candidate-carousel candidate-carousel-editor">
                <div className="candidate-carousel-header">
                  <div>
                    <strong>Candidate screenshots</strong>
                    <div className="artifact-meta">
                      Browse generated screenshots and choose the best evidence for this step.
                    </div>
                  </div>
                  <div className="artifact-meta">
                    {candidateIndex + 1} / {totalCandidates}
                  </div>
                </div>

                <div className="editor-intent-card">
                  <div className="editor-intent-title">Step intent</div>
                  <div className="editor-intent-text">{draftValues.actionText ?? step.actionText}</div>
                  {draftValues.sourceDataNote ?? step.sourceDataNote ? (
                    <div className="artifact-meta">
                      Source: {draftValues.sourceDataNote ?? step.sourceDataNote}
                    </div>
                  ) : null}
                  {draftValues.supportingTranscriptText ?? step.supportingTranscriptText ? (
                    <div className="artifact-meta">
                      Evidence: {draftValues.supportingTranscriptText ?? step.supportingTranscriptText}
                    </div>
                  ) : null}
                </div>

                <div className="candidate-carousel-body">
                  <div className="screenshot-preview candidate-preview candidate-preview-editor">
                    <AuthenticatedArtifactImage
                      artifactId={currentCandidate.artifactId}
                      alt={`Candidate screenshot ${candidateIndex + 1} for step ${step.stepNumber}`}
                    />
                  </div>
                  <div className="artifact-meta">
                    {currentCandidate.timestamp} | source {currentCandidate.sourceRole} |{" "}
                    {currentCandidate.isSelected ? "already selected" : "available"}
                  </div>
                  <div className="button-row">
                    <button type="button" className="button-secondary" onClick={onPreviousCandidate}>
                      Previous
                    </button>
                    <button type="button" className="button-secondary" onClick={onNextCandidate}>
                      Next
                    </button>
                    {currentCandidate.isSelected ? (
                      <button
                        type="button"
                        className="button-primary"
                        disabled={disabled}
                        onClick={() => void onMakeCandidatePrimary(step, currentCandidate)}
                      >
                        Make selected screenshot primary
                      </button>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="button-secondary"
                          disabled={disabled}
                          onClick={() => void onAddCandidateToStep(step, currentCandidate, false)}
                        >
                          Add screenshot to step
                        </button>
                        <button
                          type="button"
                          className="button-primary"
                          disabled={disabled}
                          onClick={() => void onAddCandidateToStep(step, currentCandidate, true)}
                        >
                          Add as primary
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="empty-state">No candidate screenshots available for this step.</div>
            )}
          </div>

          <form className="stack editor-form-column" onSubmit={(event) => void onSubmit(event)}>
            <div className="editor-form-actions">
              <button type="submit" className="button-primary" disabled={disabled}>
                Save step changes
              </button>
            </div>

            <label className="field-group">
              <span>Action text</span>
              <textarea
                ref={actionTextRef}
                rows={4}
                value={draftValues.actionText ?? ""}
                onChange={(event) => onActionTextChange(event.target.value)}
              />
            </label>

            <label className="field-group">
              <span>Source data note</span>
              <textarea
                rows={3}
                value={draftValues.sourceDataNote ?? ""}
                onChange={(event) => onSourceDataNoteChange(event.target.value)}
              />
            </label>

            <label className="field-group">
              <span>Confidence</span>
              <select
                value={draftValues.confidence ?? "medium"}
                onChange={(event) => onConfidenceChange(event.target.value as ProcessStep["confidence"])}
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
          </form>
        </div>
      </div>
    </div>
  );
}
