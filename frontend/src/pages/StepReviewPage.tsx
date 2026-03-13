/**
 * Purpose: Step review page for moderate BA edits.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\StepReviewPage.tsx
 */

import React, { useEffect, useState } from "react";

import { StepReviewPanel } from "../components/review/StepReviewPanel";
import { apiClient } from "../services/apiClient";
import type { CandidateScreenshot, ProcessStep } from "../types/process";
import type { DraftSession } from "../types/session";

type StepReviewPageProps = {
  session: DraftSession | null;
  selectedStepId: string | null;
  disabled?: boolean;
  showHeader?: boolean;
  onCloseSession?: () => void;
  onSelectStep: (stepId: string) => void;
  onSaveStep: (stepId: string, payload: Partial<ProcessStep>) => Promise<void>;
  onSetPrimaryScreenshot: (stepId: string, stepScreenshotId: string) => Promise<void>;
  onRemoveScreenshot: (stepId: string, stepScreenshotId: string) => Promise<void>;
  onSelectCandidateScreenshot: (
    stepId: string,
    candidateScreenshotId: string,
    payload?: { isPrimary?: boolean; role?: string },
  ) => Promise<void>;
};

export function StepReviewPage({
  session,
  selectedStepId,
  disabled,
  showHeader = true,
  onCloseSession,
  onSelectStep,
  onSaveStep,
  onSetPrimaryScreenshot,
  onRemoveScreenshot,
  onSelectCandidateScreenshot,
}: StepReviewPageProps): JSX.Element {
  const selectedStep = session?.processSteps.find((step) => step.id === selectedStepId) ?? session?.processSteps[0] ?? null;
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

  if (!session) {
    return (
      <section className="panel">
        <h2>3. Review Steps</h2>
        <div className="empty-state">Once draft generation completes, extracted process steps will appear here.</div>
      </section>
    );
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedStep) {
      return;
    }
    await onSaveStep(selectedStep.id, draftValues);
  }

  const currentCandidate = selectedStep?.candidateScreenshots[candidateIndex] ?? null;

  return (
    <section className="panel stack">
      {showHeader ? (
        <div>
          <h2>3. Review and Edit Steps</h2>
          <p className="muted">Validate the extracted AS-IS steps, derived screenshots, and confidence markers.</p>
        </div>
      ) : null}

      {session ? (
        <div className="section-header-inline">
          <div>
            <strong>{session.title}</strong>
            <div className="artifact-meta">
              {session.processSteps.length} step(s) | status {session.status}
            </div>
          </div>
          {onCloseSession ? (
            <button type="button" className="button-secondary" onClick={onCloseSession} disabled={disabled}>
              Close session
            </button>
          ) : null}
        </div>
      ) : null}

      {session.processSteps.length === 0 ? (
        <div className="empty-state">No steps have been generated yet.</div>
      ) : (
        <>
          <div className="review-layout">
            <div className={`step-list review-step-list ${isEditing ? "step-list-editing" : ""}`}>
              {session.processSteps.map((step) => (
                <button
                  key={step.id}
                  type="button"
                  className={`button-secondary review-step-button ${selectedStep?.id === step.id ? "review-step-button-active" : ""}`}
                  onClick={() => onSelectStep(step.id)}
                >
                  Step {step.stepNumber}: {step.actionText.slice(0, 80)}
                </button>
              ))}
            </div>

            <div className="review-detail-column">
              {selectedStep ? (
                <>
                  <StepReviewPanel
                    step={selectedStep}
                    onEdit={(step) => {
                      onSelectStep(step.id);
                      setIsEditing(true);
                    }}
                    onSetPrimaryScreenshot={(stepScreenshotId) => onSetPrimaryScreenshot(selectedStep.id, stepScreenshotId)}
                    onRemoveScreenshot={(stepScreenshotId) => onRemoveScreenshot(selectedStep.id, stepScreenshotId)}
                  />

                  {isEditing ? (
                  <div className="editor-overlay" role="dialog" aria-modal="true" aria-label={`Edit step ${selectedStep.stepNumber}`}>
                    <div className="editor-workspace">
                      <div className="editor-workspace-header">
                        <div>
                          <h3>Edit Step {selectedStep.stepNumber}</h3>
                          <div className="artifact-meta">
                            {selectedStep.applicationName || "Application pending"} | {selectedStep.timestamp || "No timestamp"}
                          </div>
                        </div>
                        <button type="button" className="button-secondary" onClick={() => setIsEditing(false)} disabled={disabled}>
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
                                  {candidateIndex + 1} / {selectedStep.candidateScreenshots.length}
                                </div>
                              </div>

                              <div className="editor-intent-card">
                                <div className="editor-intent-title">Step intent</div>
                                <div className="editor-intent-text">{draftValues.actionText ?? selectedStep.actionText}</div>
                                {draftValues.sourceDataNote ?? selectedStep.sourceDataNote ? (
                                  <div className="artifact-meta">
                                    Source: {draftValues.sourceDataNote ?? selectedStep.sourceDataNote}
                                  </div>
                                ) : null}
                                {draftValues.supportingTranscriptText ?? selectedStep.supportingTranscriptText ? (
                                  <div className="artifact-meta">
                                    Evidence: {draftValues.supportingTranscriptText ?? selectedStep.supportingTranscriptText}
                                  </div>
                                ) : null}
                              </div>

                              <div className="candidate-carousel-body">
                                <div className="screenshot-preview candidate-preview candidate-preview-editor">
                                  <img
                                    src={apiClient.getArtifactContentUrl(currentCandidate.artifactId)}
                                    alt={`Candidate screenshot ${candidateIndex + 1} for step ${selectedStep.stepNumber}`}
                                  />
                                </div>
                                <div className="artifact-meta">
                                  {currentCandidate.timestamp} | source {currentCandidate.sourceRole} |{" "}
                                  {currentCandidate.isSelected ? "already selected" : "available"}
                                </div>
                                <div className="button-row">
                                  <button
                                    type="button"
                                    className="button-secondary"
                                    onClick={() =>
                                      setCandidateIndex((current) =>
                                        current === 0 ? selectedStep.candidateScreenshots.length - 1 : current - 1,
                                      )
                                    }
                                  >
                                    Previous
                                  </button>
                                  <button
                                    type="button"
                                    className="button-secondary"
                                    onClick={() =>
                                      setCandidateIndex((current) =>
                                        current === selectedStep.candidateScreenshots.length - 1 ? 0 : current + 1,
                                      )
                                    }
                                  >
                                    Next
                                  </button>
                                  {currentCandidate.isSelected ? (
                                    <button
                                      type="button"
                                      className="button-primary"
                                      disabled={disabled}
                                      onClick={() => void makeCandidatePrimary(selectedStep, currentCandidate)}
                                    >
                                      Make selected screenshot primary
                                    </button>
                                  ) : (
                                    <>
                                      <button
                                        type="button"
                                        className="button-secondary"
                                        disabled={disabled}
                                        onClick={() => void addCandidateToStep(selectedStep, currentCandidate, false)}
                                      >
                                        Add screenshot to step
                                      </button>
                                      <button
                                        type="button"
                                        className="button-primary"
                                        disabled={disabled}
                                        onClick={() => void addCandidateToStep(selectedStep, currentCandidate, true)}
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

                        <form className="stack editor-form-column" onSubmit={handleSubmit}>
                          <div className="editor-form-actions">
                            <button type="submit" className="button-primary" disabled={disabled}>
                              Save step changes
                            </button>
                          </div>

                          <label className="field-group">
                            <span>Action text</span>
                            <textarea
                              rows={5}
                              value={draftValues.actionText ?? ""}
                              onChange={(event) => setDraftValues((current) => ({ ...current, actionText: event.target.value }))}
                            />
                          </label>

                          <label className="field-group">
                            <span>Source data note</span>
                            <textarea
                              rows={4}
                              value={draftValues.sourceDataNote ?? ""}
                              onChange={(event) => setDraftValues((current) => ({ ...current, sourceDataNote: event.target.value }))}
                            />
                          </label>

                          <label className="field-group">
                            <span>Confidence</span>
                            <select
                              value={draftValues.confidence ?? "medium"}
                              onChange={(event) =>
                                setDraftValues((current) => ({
                                  ...current,
                                  confidence: event.target.value as ProcessStep["confidence"],
                                }))
                              }
                            >
                              <option value="high">High</option>
                              <option value="medium">Medium</option>
                              <option value="low">Low</option>
                              <option value="unknown">Unknown</option>
                            </select>
                          </label>

                          <div className="button-row">
                            <button type="submit" className="button-primary" disabled={disabled}>
                              Save step changes
                            </button>
                          </div>
                        </form>
                      </div>
                    </div>
                  </div>
                  ) : null}
                </>
              ) : null}
            </div>
          </div>
        </>
      )}
    </section>
  );

  async function addCandidateToStep(step: ProcessStep, candidate: CandidateScreenshot, makePrimary: boolean) {
    await onSelectCandidateScreenshot(step.id, candidate.id, { isPrimary: makePrimary });
  }

  async function makeCandidatePrimary(step: ProcessStep, candidate: CandidateScreenshot) {
    await onSelectCandidateScreenshot(step.id, candidate.id, { isPrimary: true });
  }
}
