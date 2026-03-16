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
  onEdit?: (step: ProcessStep) => void;
  onSetPrimaryScreenshot?: (stepScreenshotId: string) => void;
  onRemoveScreenshot?: (stepScreenshotId: string) => void;
  readOnly?: boolean;
};

export function StepReviewPanel({
  step,
  onEdit,
  onSetPrimaryScreenshot,
  onRemoveScreenshot,
  readOnly = false,
}: StepReviewPanelProps): JSX.Element {
  const primaryScreenshot =
    step.screenshots.find((stepScreenshot) => stepScreenshot.isPrimary) ?? step.screenshots[0] ?? null;
  const secondaryScreenshots = primaryScreenshot
    ? step.screenshots.filter((stepScreenshot) => stepScreenshot.id !== primaryScreenshot.id)
    : [];

  return (
    <article className="step-card">
      <div className="step-card-header">
        <div>
          <strong>Step {step.stepNumber}</strong>
          <div className="step-meta">
            {step.applicationName || "Application pending"} {step.timestamp ? `| ${step.timestamp}` : ""}
          </div>
        </div>
        <div className="step-card-header-actions">
          <ConfidenceBadge level={step.confidence} />
          {!readOnly && onEdit ? (
            <button type="button" className="button-secondary" onClick={() => onEdit(step)}>
              Edit step
            </button>
          ) : null}
        </div>
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
        {primaryScreenshot ? (
          <div className="stack">
            <div className="step-screenshot-section">
              <div className="step-section-title">Primary screenshot</div>
              <div className="screenshot-card screenshot-card-primary">
                <div className="screenshot-preview screenshot-preview-primary">
                  <span className="screenshot-badge">Primary</span>
                  <img
                    src={apiClient.getArtifactContentUrl(primaryScreenshot.artifactId)}
                    alt={`Primary screenshot for step ${step.stepNumber}`}
                  />
                </div>
                <div className="artifact-meta">
                  {primaryScreenshot.role} | {primaryScreenshot.timestamp}
                </div>
                {!readOnly && onRemoveScreenshot ? (
                  <div className="button-row">
                    <button type="button" className="button-danger" onClick={() => onRemoveScreenshot(primaryScreenshot.id)}>
                      Remove screenshot
                    </button>
                  </div>
                ) : null}
              </div>
            </div>

            {secondaryScreenshots.length > 0 ? (
              <div className="step-screenshot-section">
                <div className="step-section-title">Other screenshots</div>
                <div className="screenshot-grid">
                  {secondaryScreenshots.map((stepScreenshot) => (
                    <div key={stepScreenshot.id} className="screenshot-card">
                      <div className="screenshot-preview">
                        <img
                          src={apiClient.getArtifactContentUrl(stepScreenshot.artifactId)}
                          alt={`${stepScreenshot.role} screenshot for step ${step.stepNumber}`}
                        />
                      </div>
                      <div className="artifact-meta">
                        {stepScreenshot.role} | {stepScreenshot.timestamp} | secondary
                      </div>
                      {!readOnly && onSetPrimaryScreenshot && onRemoveScreenshot ? (
                        <div className="button-row">
                          <button type="button" className="button-secondary" onClick={() => onSetPrimaryScreenshot(stepScreenshot.id)}>
                            Make primary
                          </button>
                          <button type="button" className="button-danger" onClick={() => onRemoveScreenshot(stepScreenshot.id)}>
                            Remove screenshot
                          </button>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="screenshot-card">
            <div className="screenshot-preview">
              <span className="muted">No derived screenshot available yet.</span>
            </div>
          </div>
        )}
        <div className="artifact-meta">
          Evidence:{" "}
          {step.evidenceReferences.length > 0
            ? step.evidenceReferences.map((reference) => `${reference.kind}:${reference.locator}`).join(", ")
            : "No evidence mapped"}
        </div>
      </div>
    </article>
  );
}
