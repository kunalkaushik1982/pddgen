/**
 * Purpose: Step review page for moderate BA edits.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\StepReviewPage.tsx
 */

import React, { useEffect, useState } from "react";

import { StepReviewPanel } from "../components/review/StepReviewPanel";
import type { ProcessStep } from "../types/process";
import type { DraftSession } from "../types/session";

type StepReviewPageProps = {
  session: DraftSession | null;
  selectedStepId: string | null;
  disabled?: boolean;
  onSelectStep: (stepId: string) => void;
  onSaveStep: (stepId: string, payload: Partial<ProcessStep>) => Promise<void>;
  onSetPrimaryScreenshot: (stepId: string, stepScreenshotId: string) => Promise<void>;
  onRemoveScreenshot: (stepId: string, stepScreenshotId: string) => Promise<void>;
};

export function StepReviewPage({
  session,
  selectedStepId,
  disabled,
  onSelectStep,
  onSaveStep,
  onSetPrimaryScreenshot,
  onRemoveScreenshot,
}: StepReviewPageProps): JSX.Element {
  const selectedStep = session?.processSteps.find((step) => step.id === selectedStepId) ?? session?.processSteps[0] ?? null;
  const [draftValues, setDraftValues] = useState<Partial<ProcessStep>>({});
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    setDraftValues(
      selectedStep
        ? {
            applicationName: selectedStep.applicationName,
            actionText: selectedStep.actionText,
            sourceDataNote: selectedStep.sourceDataNote,
            timestamp: selectedStep.timestamp,
            startTimestamp: selectedStep.startTimestamp,
            endTimestamp: selectedStep.endTimestamp,
            supportingTranscriptText: selectedStep.supportingTranscriptText,
            confidence: selectedStep.confidence,
          }
        : {},
    );
    setIsEditing(false);
  }, [selectedStep]);

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

  return (
    <section className="panel stack">
      <div>
        <h2>3. Review and Edit Steps</h2>
        <p className="muted">Validate the extracted AS-IS steps, derived screenshots, and confidence markers.</p>
      </div>

      {session.processSteps.length === 0 ? (
        <div className="empty-state">No steps have been generated yet.</div>
      ) : (
        <>
          <div className="step-list">
            {session.processSteps.map((step) => (
              <button
                key={step.id}
                type="button"
                className="button-secondary"
                onClick={() => onSelectStep(step.id)}
              >
                Step {step.stepNumber}: {step.actionText.slice(0, 80)}
              </button>
            ))}
          </div>

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
              <form className="stack" onSubmit={handleSubmit}>
                <div className="field-inline">
                  <label className="field-group">
                    <span>Application</span>
                    <input
                      value={draftValues.applicationName ?? ""}
                      onChange={(event) => setDraftValues((current) => ({ ...current, applicationName: event.target.value }))}
                    />
                  </label>
                  <label className="field-group">
                    <span>Display timestamp</span>
                    <input
                      value={draftValues.timestamp ?? ""}
                      onChange={(event) => setDraftValues((current) => ({ ...current, timestamp: event.target.value }))}
                    />
                  </label>
                </div>

                <div className="field-inline">
                  <label className="field-group">
                    <span>Evidence start</span>
                    <input
                      value={draftValues.startTimestamp ?? ""}
                      onChange={(event) =>
                        setDraftValues((current) => ({ ...current, startTimestamp: event.target.value }))
                      }
                    />
                  </label>
                  <label className="field-group">
                    <span>Evidence end</span>
                    <input
                      value={draftValues.endTimestamp ?? ""}
                      onChange={(event) =>
                        setDraftValues((current) => ({ ...current, endTimestamp: event.target.value }))
                      }
                    />
                  </label>
                </div>

                <label className="field-group">
                  <span>Action text</span>
                  <textarea
                    rows={4}
                    value={draftValues.actionText ?? ""}
                    onChange={(event) => setDraftValues((current) => ({ ...current, actionText: event.target.value }))}
                  />
                </label>

                <label className="field-group">
                  <span>Source data note</span>
                  <textarea
                    rows={3}
                    value={draftValues.sourceDataNote ?? ""}
                    onChange={(event) => setDraftValues((current) => ({ ...current, sourceDataNote: event.target.value }))}
                  />
                </label>

                <label className="field-group">
                  <span>Supporting transcript evidence</span>
                  <textarea
                    rows={4}
                    value={draftValues.supportingTranscriptText ?? ""}
                    onChange={(event) =>
                      setDraftValues((current) => ({
                        ...current,
                        supportingTranscriptText: event.target.value,
                      }))
                    }
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
                  <button type="button" className="button-secondary" onClick={() => setIsEditing(false)} disabled={disabled}>
                    Close editor
                  </button>
                </div>
              </form>
              ) : null}
            </>
          ) : null}

          <div className="note-list">
            <h3>Extracted business notes</h3>
            {session.processNotes.length > 0 ? (
              session.processNotes.map((note) => (
                <div key={note.id} className="note-card">
                  <div>{note.text}</div>
                  <div className="artifact-meta">
                    {note.inferenceType} | {note.confidence}
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">No rule-like transcript notes were detected.</div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
