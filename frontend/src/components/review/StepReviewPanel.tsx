/**
 * Purpose: Placeholder review panel for one extracted process step and its evidence.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\review\StepReviewPanel.tsx
 */

import React from "react";

import type { ProcessStep } from "../../types/process";
import { apiClient } from "../../services/apiClient";
import { ConfidenceBadge } from "./ConfidenceBadge";

type StepReviewPanelProps = {
  step: ProcessStep;
  onEdit: (step: ProcessStep) => void;
  onSetPrimaryScreenshot: (stepScreenshotId: string) => void;
  onRemoveScreenshot: (stepScreenshotId: string) => void;
};

export function StepReviewPanel({
  step,
  onEdit,
  onSetPrimaryScreenshot,
  onRemoveScreenshot,
}: StepReviewPanelProps): JSX.Element {
  return (
    <article className="step-card">
      <div className="step-card-header">
        <div>
          <strong>Step {step.stepNumber}</strong>
          <div className="step-meta">
            {step.applicationName || "Application pending"} {step.timestamp ? `| ${step.timestamp}` : ""}
          </div>
        </div>
        <ConfidenceBadge level={step.confidence} />
      </div>

      <div>{step.actionText}</div>

      {step.sourceDataNote ? <div className="muted">Source data: {step.sourceDataNote}</div> : null}
      {step.startTimestamp || step.endTimestamp ? (
        <div className="muted">
          Evidence window: {step.startTimestamp || "-"} to {step.endTimestamp || "-"}
        </div>
      ) : null}
      {step.supportingTranscriptText ? (
        <div className="muted">Transcript evidence: {step.supportingTranscriptText}</div>
      ) : null}

      <div className="step-preview">
        {step.screenshots.length > 0 ? (
          <div className="stack">
            {step.screenshots.map((stepScreenshot) => (
              <div key={stepScreenshot.id} className="screenshot-preview">
                <img
                  src={apiClient.getArtifactContentUrl(stepScreenshot.artifactId)}
                  alt={`${stepScreenshot.role} screenshot for step ${step.stepNumber}`}
                />
                <div className="artifact-meta">
                  {stepScreenshot.role} | {stepScreenshot.timestamp} | {stepScreenshot.isPrimary ? "primary" : "secondary"}
                </div>
                <div className="button-row">
                  {!stepScreenshot.isPrimary ? (
                    <button type="button" className="button-secondary" onClick={() => onSetPrimaryScreenshot(stepScreenshot.id)}>
                      Make primary
                    </button>
                  ) : null}
                  <button type="button" className="button-secondary" onClick={() => onRemoveScreenshot(stepScreenshot.id)}>
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="screenshot-preview">
            <span className="muted">No derived screenshot available yet.</span>
          </div>
        )}
        <div className="artifact-meta">
          Evidence:{" "}
          {step.evidenceReferences.length > 0
            ? step.evidenceReferences.map((reference) => `${reference.kind}:${reference.locator}`).join(", ")
            : "No evidence mapped"}
        </div>
      </div>

      <div className="step-card-actions">
        <button type="button" className="button-secondary" onClick={() => onEdit(step)}>
          Edit step
        </button>
      </div>
    </article>
  );
}
