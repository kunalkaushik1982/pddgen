/**
 * Purpose: Step review page for moderate BA edits.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\StepReviewPage.tsx
 */

import React, { useEffect, useState } from "react";

import { FlowchartPreviewPanel } from "../components/diagram/FlowchartPreviewPanel";
import { SessionChatPanel } from "../components/review/SessionChatPanel";
import { StepReviewPanel } from "../components/review/StepReviewPanel";
import { apiClient } from "../services/apiClient";
import type { CandidateScreenshot, ProcessStep } from "../types/process";
import type { DraftSession, SessionAnswer } from "../types/session";

type ReviewMode = "view" | "edit";
type ViewWorkspaceTab = "summary" | "steps" | "diagram" | "ask" | "log";
type EditWorkspaceTab = "steps" | "diagram";
type SessionChatEntry = {
  id: string;
  question: string;
  answer: SessionAnswer;
};

type StepReviewPageProps = {
  session: DraftSession | null;
  selectedStepId: string | null;
  initialReviewMode?: ReviewMode;
  disabled?: boolean;
  showHeader?: boolean;
  headerActions?: React.ReactNode;
  onCloseSession?: () => void;
  onSelectStep: (stepId: string) => void;
  onSaveStep: (stepId: string, payload: Partial<ProcessStep>) => Promise<void>;
  onSetPrimaryScreenshot: (stepId: string, stepScreenshotId: string) => Promise<void>;
  onRemoveScreenshot: (stepId: string, stepScreenshotId: string) => Promise<void>;
  onRefreshSession?: () => Promise<void> | void;
  onSelectCandidateScreenshot: (
    stepId: string,
    candidateScreenshotId: string,
    payload?: { isPrimary?: boolean; role?: string },
  ) => Promise<void>;
};

export function StepReviewPage({
  session,
  selectedStepId,
  initialReviewMode = "view",
  disabled,
  showHeader = true,
  headerActions,
  onCloseSession,
  onSelectStep,
  onSaveStep,
  onSetPrimaryScreenshot,
  onRemoveScreenshot,
  onRefreshSession,
  onSelectCandidateScreenshot,
}: StepReviewPageProps): JSX.Element {
  const selectedStep = session?.processSteps.find((step) => step.id === selectedStepId) ?? session?.processSteps[0] ?? null;
  const [draftValues, setDraftValues] = useState<Partial<ProcessStep>>({});
  const [isEditing, setIsEditing] = useState(false);
  const [candidateIndex, setCandidateIndex] = useState(0);
  const [reviewMode, setReviewMode] = useState<ReviewMode>(initialReviewMode);
  const [activeViewTab, setActiveViewTab] = useState<ViewWorkspaceTab>("summary");
  const [activeEditTab, setActiveEditTab] = useState<EditWorkspaceTab>("steps");
  const [chatEntries, setChatEntries] = useState<SessionChatEntry[]>([]);
  const [chatError, setChatError] = useState<string | null>(null);

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

  useEffect(() => {
    setReviewMode(initialReviewMode);
    setActiveViewTab("summary");
    setActiveEditTab("steps");
    setChatEntries([]);
    setChatError(null);
  }, [initialReviewMode, session?.id]);

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
  const applications = Array.from(new Set(session.processSteps.map((step) => step.applicationName).filter(Boolean)));
  const editedSteps = session.processSteps.filter((step) => step.editedByBa);
  const screenshotCount = session.processSteps.reduce((total, step) => total + step.screenshots.length, 0);
  const primaryScreenshotCount = session.processSteps.reduce(
    (total, step) => total + step.screenshots.filter((screenshot) => screenshot.isPrimary).length,
    0,
  );
  const summaryHeading = session.processNotes[0]?.text || "SME Process Walkthrough";
  const summarySubheading = applications.length > 0 ? applications.join(" and ") : "Process Overview";
  const summaryBullets = session.processSteps.slice(0, 12).map((step) => step.actionText);
  const actionLogEntries = session.actionLogs;

  function switchMode(nextMode: ReviewMode) {
    setReviewMode(nextMode);
    if (nextMode === "edit") {
      if (activeViewTab === "diagram") {
        setActiveEditTab("diagram");
      } else {
        setActiveEditTab("steps");
      }
      return;
    }
    if (activeEditTab === "diagram") {
      setActiveViewTab("diagram");
    } else if (activeViewTab === "summary" || activeViewTab === "log") {
      setActiveViewTab(activeViewTab);
    } else {
      setActiveViewTab("steps");
    }
  }

  return (
    <section className="panel stack">
      {showHeader ? (
        <div>
          <h2>3. Review and Edit Steps</h2>
          <p className="muted">Validate the extracted AS-IS steps, derived screenshots, and confidence markers.</p>
        </div>
      ) : null}

      <div className="section-header-inline">
        <div>
          <strong>{session.title}</strong>
          <div className="artifact-meta">
            {session.processSteps.length} step(s) | status {session.status}
          </div>
        </div>
        <div className="review-header-actions">
          {headerActions}
          <div className="review-mode-switch" role="tablist" aria-label="Review mode">
            <button
              type="button"
              role="tab"
              aria-selected={reviewMode === "view"}
              className={`review-mode-tab ${reviewMode === "view" ? "review-mode-tab-active" : ""}`}
              onClick={() => switchMode("view")}
            >
              View
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={reviewMode === "edit"}
              className={`review-mode-tab ${reviewMode === "edit" ? "review-mode-tab-active" : ""}`}
              onClick={() => switchMode("edit")}
            >
              Edit
            </button>
          </div>
          {onCloseSession ? (
            <button type="button" className="button-secondary" onClick={onCloseSession} disabled={disabled}>
              Close session
            </button>
          ) : null}
        </div>
      </div>

      {session.processSteps.length === 0 ? (
        <div className="empty-state">No steps have been generated yet.</div>
      ) : (
        <div className="review-subsection-stack">
          {reviewMode === "view" ? (
            <div className="review-workspace-tabs" role="tablist" aria-label="View workspace">
              <button
                type="button"
                role="tab"
                aria-selected={activeViewTab === "summary"}
                className={`review-workspace-tab ${activeViewTab === "summary" ? "review-workspace-tab-active" : ""}`}
                onClick={() => setActiveViewTab("summary")}
              >
                Summary
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeViewTab === "steps"}
                className={`review-workspace-tab ${activeViewTab === "steps" ? "review-workspace-tab-active" : ""}`}
                onClick={() => setActiveViewTab("steps")}
              >
                Process
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeViewTab === "diagram"}
                className={`review-workspace-tab ${activeViewTab === "diagram" ? "review-workspace-tab-active" : ""}`}
                onClick={() => setActiveViewTab("diagram")}
              >
                Diagram
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeViewTab === "ask"}
                className={`review-workspace-tab ${activeViewTab === "ask" ? "review-workspace-tab-active" : ""}`}
                onClick={() => setActiveViewTab("ask")}
              >
                Ask
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeViewTab === "log"}
                className={`review-workspace-tab ${activeViewTab === "log" ? "review-workspace-tab-active" : ""}`}
                onClick={() => setActiveViewTab("log")}
              >
                Action Log
              </button>
            </div>
          ) : (
            <div className="review-workspace-tabs" role="tablist" aria-label="Edit workspace">
              <button
                type="button"
                role="tab"
                aria-selected={activeEditTab === "steps"}
                className={`review-workspace-tab ${activeEditTab === "steps" ? "review-workspace-tab-active" : ""}`}
                onClick={() => setActiveEditTab("steps")}
              >
                Process
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeEditTab === "diagram"}
                className={`review-workspace-tab ${activeEditTab === "diagram" ? "review-workspace-tab-active" : ""}`}
                onClick={() => setActiveEditTab("diagram")}
              >
                Diagram
              </button>
            </div>
          )}

          {reviewMode === "view" && activeViewTab === "summary" ? (
            <section className="review-subsection panel stack" role="tabpanel" aria-label="Summary">
              <div>
                <h3>Summary</h3>
                <div className="artifact-meta">Narrative summary for review before detailed process editing or export.</div>
              </div>

              <div className="summary-document">
                <div className="summary-document-label">Process summary</div>
                <div className="summary-document-card">
                  <h4 className="summary-document-title">{summaryHeading}</h4>
                  <div className="summary-document-subtitle">{summarySubheading}</div>
                  <ul className="summary-document-list">
                    {summaryBullets.map((bullet, index) => (
                      <li key={`${index}_${bullet}`}>{bullet}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="summary-meta-grid">
                <div className="summary-meta-card">
                  <div className="artifact-meta">Session</div>
                  <strong>{session.title}</strong>
                  <div className="summary-muted">{session.processSteps.length} steps | {session.diagramType}</div>
                </div>
                <div className="summary-meta-card">
                  <div className="artifact-meta">Applications</div>
                  <strong>{applications.length > 0 ? applications.join(", ") : "Not detected"}</strong>
                  <div className="summary-muted">{applications.length} application(s) involved</div>
                </div>
                <div className="summary-meta-card">
                  <div className="artifact-meta">Evidence</div>
                  <strong>{screenshotCount} screenshots</strong>
                  <div className="summary-muted">{primaryScreenshotCount} primary selections</div>
                </div>
                <div className="summary-meta-card">
                  <div className="artifact-meta">BA edits</div>
                  <strong>{editedSteps.length} edited steps</strong>
                  <div className="summary-muted">{session.processNotes.length} notes captured</div>
                </div>
              </div>

            </section>
          ) : null}

          {reviewMode === "view" && activeViewTab === "diagram" ? (
            <section className="review-subsection panel stack" role="tabpanel" aria-label="Diagram view">
              <div>
                <h3>Diagram</h3>
                <div className="artifact-meta">Read-only process diagram preview.</div>
              </div>
              <FlowchartPreviewPanel session={session} allowEditing={false} onSessionRefresh={onRefreshSession} />
            </section>
          ) : null}

          {reviewMode === "view" && activeViewTab === "ask" ? (
            <SessionChatPanel
              disabled={disabled}
              errorMessage={chatError}
              entries={chatEntries}
              onAsk={handleAskSession}
            />
          ) : null}

          {reviewMode === "edit" && activeEditTab === "diagram" ? (
            <section className="review-subsection panel stack" role="tabpanel" aria-label="Diagram editor">
              <div>
                <h3>Diagram Editor</h3>
                <div className="artifact-meta">Edit the saved detailed process diagram used in review and export.</div>
              </div>
              <FlowchartPreviewPanel session={session} allowEditing onSessionRefresh={onRefreshSession} />
            </section>
          ) : null}

          {reviewMode === "view" && activeViewTab === "steps" ? (
            <section className="review-subsection panel stack" role="tabpanel" aria-label="Process view">
              <div>
                <h3>Process</h3>
                <div className="artifact-meta">Read-only process step review with screenshots and evidence.</div>
              </div>

              <div className="review-layout">
                <div className="step-list review-step-list">
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
                    <StepReviewPanel
                      step={selectedStep}
                      readOnly
                    />
                  ) : null}
                </div>
              </div>
            </section>
          ) : null}

          {reviewMode === "edit" && activeEditTab === "steps" ? (
            <section className="review-subsection panel stack" role="tabpanel" aria-label="Process step editor">
              <div>
                <h3>Process Step Editor</h3>
                <div className="artifact-meta">Review screenshots, update extracted step text, and save BA corrections.</div>
              </div>

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
                                        {currentCandidate.timestamp} | source {currentCandidate.sourceRole} | {" "}
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

                              </form>
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </>
                  ) : null}
                </div>
              </div>
            </section>
          ) : null}

          {reviewMode === "view" && activeViewTab === "log" ? (
            <section className="review-subsection panel stack" role="tabpanel" aria-label="Action log">
              <div>
                <h3>Action Log</h3>
                <div className="artifact-meta">Meaningful session events that affect the final PDD output.</div>
              </div>

              {actionLogEntries.length > 0 ? (
                <div className="summary-document">
                  <div className="summary-document-label">Session activity</div>
                  <div className="summary-document-card action-log-document-card">
                    <div className="summary-document-title">Review and export activity</div>
                    <ul className="action-log-document-list">
                      {actionLogEntries.map((entry) => (
                        <li key={entry.id} className="action-log-document-item">
                          <div className="action-log-document-title">{entry.title}</div>
                          <div className="action-log-document-detail">{entry.detail}</div>
                          <div className="artifact-meta">
                            {entry.actor} | {new Date(entry.createdAt).toLocaleString()}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <div className="empty-state">No session activity is available yet.</div>
              )}
            </section>
          ) : null}
        </div>
      )}
    </section>
  );

  async function addCandidateToStep(step: ProcessStep, candidate: CandidateScreenshot, makePrimary: boolean) {
    await onSelectCandidateScreenshot(step.id, candidate.id, { isPrimary: makePrimary });
  }

  async function makeCandidatePrimary(step: ProcessStep, candidate: CandidateScreenshot) {
    await onSelectCandidateScreenshot(step.id, candidate.id, { isPrimary: true });
  }

  async function handleAskSession(question: string) {
    if (!session) {
      return;
    }

    setChatError(null);
    try {
      const answer = await apiClient.askSession(session.id, question);
      setChatEntries((current) => [
        {
          id: `${Date.now()}_${current.length}`,
          question,
          answer,
        },
        ...current,
      ]);
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "Ask this Session could not answer that question.");
    }
  }
}
