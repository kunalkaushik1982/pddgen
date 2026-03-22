/**
 * Purpose: Step review page for moderate BA edits.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\StepReviewPage.tsx
 */

import React, { Suspense, lazy } from "react";

import { ReviewWorkspaceTabs } from "../components/review/ReviewWorkspaceTabs";
import { uiCopy } from "../constants/uiCopy";
import { SessionActionLogPanel } from "../components/review/SessionActionLogPanel";
import { SessionDiagramSection } from "../components/review/SessionDiagramSection";
import { SessionProcessSection } from "../components/review/SessionProcessSection";
import { SessionSummaryPanel } from "../components/review/SessionSummaryPanel";
import { useAskSession } from "../hooks/useAskSession";
import { useReviewWorkspace, type ReviewMode } from "../hooks/useReviewWorkspace";
import { useStepEditor } from "../hooks/useStepEditor";
import type { ProcessStep } from "../types/process";
import type { DraftSession } from "../types/session";

const FlowchartPreviewPanel = lazy(async () => {
  const module = await import("../components/diagram/FlowchartPreviewPanel");
  return { default: module.FlowchartPreviewPanel };
});

const SessionChatPanel = lazy(async () => {
  const module = await import("../components/review/SessionChatPanel");
  return { default: module.SessionChatPanel };
});

type StepReviewPageProps = {
  session: DraftSession | null;
  meetingSection?: React.ReactNode;
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
  meetingSection = null,
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
}: StepReviewPageProps): React.JSX.Element {
  if (!session) {
    return (
      <section className="panel">
        <h2>3. Review Steps</h2>
        <div className="empty-state">Once draft generation completes, extracted process steps will appear here.</div>
      </section>
    );
  }

  const workspace = useReviewWorkspace({
    initialReviewMode,
    sessionId: session?.id ?? null,
  });
  const stepCountByProcessGroup = React.useMemo(() => {
    const counts = new Map<string, number>();
    for (const step of session.processSteps) {
      if (!step.processGroupId) {
        continue;
      }
      counts.set(step.processGroupId, (counts.get(step.processGroupId) ?? 0) + 1);
    }
    return counts;
  }, [session.processSteps]);
  const availableProcessGroups = [...session.processGroups]
    .sort((left, right) => left.displayOrder - right.displayOrder)
    .filter((group) => {
      const stepCount = stepCountByProcessGroup.get(group.id) ?? 0;
      const normalizedTitle = group.title.trim().toLowerCase();
      const isDefaultUnnamedGroup = /^process\s+\d+$/.test(normalizedTitle);
      if (isDefaultUnnamedGroup && stepCount === 0) {
        return false;
      }
      return true;
    });
  const fallbackProcessGroupId = availableProcessGroups[0]?.id ?? null;
  const [selectedProcessGroupId, setSelectedProcessGroupId] = React.useState<string | null>(fallbackProcessGroupId);

  React.useEffect(() => {
    if (availableProcessGroups.length === 0) {
      setSelectedProcessGroupId(null);
      return;
    }
    if (!selectedProcessGroupId || availableProcessGroups.every((group) => group.id !== selectedProcessGroupId)) {
      setSelectedProcessGroupId(availableProcessGroups[0]?.id ?? null);
    }
  }, [availableProcessGroups, selectedProcessGroupId]);

  const activeProcessGroup =
    availableProcessGroups.find((group) => group.id === selectedProcessGroupId) ?? availableProcessGroups[0] ?? null;
  const filteredSteps = activeProcessGroup
    ? session.processSteps.filter((step) => (step.processGroupId ?? null) === activeProcessGroup.id)
    : session.processSteps;
  const filteredNotes = activeProcessGroup
    ? session.processNotes.filter((note) => (note.processGroupId ?? null) === activeProcessGroup.id)
    : session.processNotes;
  const selectedStep = filteredSteps.find((step) => step.id === selectedStepId) ?? filteredSteps[0] ?? null;
  const askSession = useAskSession(session, activeProcessGroup?.id ?? null);
  const stepEditor = useStepEditor(selectedStep);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedStep) {
      return;
    }
    await onSaveStep(selectedStep.id, stepEditor.draftValues);
  }

  const currentCandidate = stepEditor.currentCandidate;
  const applications = Array.from(new Set(filteredSteps.map((step) => step.applicationName).filter(Boolean)));
  const editedSteps = filteredSteps.filter((step) => step.editedByBa);
  const screenshotCount = filteredSteps.reduce((total, step) => total + step.screenshots.length, 0);
  const primaryScreenshotCount = filteredSteps.reduce(
    (total, step) => total + step.screenshots.filter((screenshot) => screenshot.isPrimary).length,
    0,
  );
  const summaryHeading = activeProcessGroup?.title || filteredNotes[0]?.text || uiCopy.summaryHeadingFallback;
  const summarySubheading = applications.length > 0 ? applications.join(" and ") : uiCopy.summarySubheadingFallback;
  const summaryBullets = filteredSteps.slice(0, 12).map((step) => step.actionText);
  const actionLogEntries = session.actionLogs;

  function renderLazyPanel(children: React.ReactNode, message: string) {
    return (
      <Suspense
        fallback={
          <div className="empty-state">
            {message}
          </div>
        }
      >
        {children}
      </Suspense>
    );
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
            {filteredSteps.length} step(s) | status {session.status}
          </div>
        </div>
        <div className="review-header-actions">
          {headerActions}
          <div className="review-mode-switch" role="tablist" aria-label="Review mode">
            <button
              type="button"
              role="tab"
              aria-selected={workspace.reviewMode === "view"}
              className={`review-mode-tab ${workspace.reviewMode === "view" ? "review-mode-tab-active" : ""}`}
              onClick={() => workspace.switchMode("view")}
            >
              View
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={workspace.reviewMode === "edit"}
              className={`review-mode-tab ${workspace.reviewMode === "edit" ? "review-mode-tab-active" : ""}`}
              onClick={() => workspace.switchMode("edit")}
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
          {availableProcessGroups.length > 1 ? (
            <div className="process-group-switcher panel">
              <div className="process-group-switcher-header">
                <strong>Detected Processes</strong>
                <span className="artifact-meta">Switch the review surface between independent workflows in this session.</span>
              </div>
              <div className="process-group-pill-row" role="tablist" aria-label="Detected process groups">
                {availableProcessGroups.map((group) => (
                  <button
                    key={group.id}
                    type="button"
                    role="tab"
                    aria-selected={activeProcessGroup?.id === group.id}
                    className={`process-group-pill ${activeProcessGroup?.id === group.id ? "process-group-pill-active" : ""}`}
                    onClick={() => setSelectedProcessGroupId(group.id)}
                  >
                    {group.title}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <ReviewWorkspaceTabs
            reviewMode={workspace.reviewMode}
            activeViewTab={workspace.activeViewTab}
            activeEditTab={workspace.activeEditTab}
            onSelectViewTab={workspace.setActiveViewTab}
            onSelectEditTab={workspace.setActiveEditTab}
          />

          {workspace.reviewMode === "view" && workspace.activeViewTab === "summary" ? (
            <section role="tabpanel" id="review-view-panel-summary" aria-labelledby="review-view-tab-summary">
              <SessionSummaryPanel
                heading={summaryHeading}
                subheading={summarySubheading}
                summaryBullets={summaryBullets}
                sessionTitle={activeProcessGroup?.title ?? session.title}
                stepCount={filteredSteps.length}
                diagramType={session.diagramType}
                applicationsLabel={applications.length > 0 ? applications.join(", ") : "Not detected"}
                applicationCount={applications.length}
                screenshotCount={screenshotCount}
                primaryScreenshotCount={primaryScreenshotCount}
                editedStepCount={editedSteps.length}
                noteCount={filteredNotes.length}
              />
            </section>
          ) : null}

          {workspace.reviewMode === "view" && workspace.activeViewTab === "diagram" ? (
            <SessionDiagramSection
              panelId="review-view-panel-diagram"
              labelledBy="review-view-tab-diagram"
              title="Diagram"
              subtitle={
                activeProcessGroup
                  ? `Showing diagram for ${activeProcessGroup.title}.`
                  : "Read-only process diagram preview."
              }
            >
              {renderLazyPanel(
                <FlowchartPreviewPanel
                  session={session}
                  allowEditing={false}
                  onSessionRefresh={onRefreshSession}
                  processGroupId={activeProcessGroup?.id ?? null}
                />,
                "Loading diagram preview...",
              )}
            </SessionDiagramSection>
          ) : null}

          {workspace.reviewMode === "view" && workspace.activeViewTab === "ask" ? (
            <section role="tabpanel" id="review-view-panel-ask" aria-labelledby="review-view-tab-ask">
              {renderLazyPanel(
            <SessionChatPanel
              disabled={disabled}
              isAsking={askSession.isAsking}
              errorMessage={askSession.errorMessage}
              entries={askSession.entries}
              selectedEvidence={askSession.selectedEvidence}
                  onSelectCitation={askSession.selectCitation}
                  onAsk={askSession.ask}
                />,
                "Loading session Q&A...",
              )}
            </section>
          ) : null}

          {workspace.reviewMode === "edit" && workspace.activeEditTab === "diagram" ? (
            <SessionDiagramSection
              panelId="review-edit-panel-diagram"
              labelledBy="review-edit-tab-diagram"
              title="Diagram Editor"
              subtitle={
                activeProcessGroup
                  ? `Editing diagram for ${activeProcessGroup.title}. Layout positions remain session-level for now.`
                  : "Edit the saved detailed process diagram used in review and export."
              }
            >
              {renderLazyPanel(
                <FlowchartPreviewPanel
                  session={session}
                  allowEditing
                  onSessionRefresh={onRefreshSession}
                  processGroupId={activeProcessGroup?.id ?? null}
                />,
                "Loading diagram editor...",
              )}
            </SessionDiagramSection>
          ) : null}

          {workspace.reviewMode === "view" && workspace.activeViewTab === "steps" ? (
            <SessionProcessSection
              panelId="review-view-panel-steps"
              labelledBy="review-view-tab-steps"
              title="Process"
              subtitle="Read-only process step review with screenshots and evidence."
              mode="view"
              stepEditor={stepEditor}
              selectedStep={selectedStep}
              steps={filteredSteps}
              selectedStepId={selectedStep?.id ?? null}
              disabled={disabled}
              onSelectStep={onSelectStep}
              onSaveStep={handleSubmit}
              onSetPrimaryScreenshot={async () => undefined}
              onRemoveScreenshot={async () => undefined}
              onSelectCandidateScreenshot={async () => undefined}
            />
          ) : null}

          {workspace.reviewMode === "edit" && workspace.activeEditTab === "steps" ? (
            <SessionProcessSection
              panelId="review-edit-panel-steps"
              labelledBy="review-edit-tab-steps"
              title="Process Step Editor"
              subtitle="Review screenshots, update extracted step text, and save BA corrections."
              mode="edit"
              stepEditor={stepEditor}
              selectedStep={selectedStep}
              steps={filteredSteps}
              selectedStepId={selectedStep?.id ?? null}
              disabled={disabled}
              onSelectStep={onSelectStep}
              onSaveStep={handleSubmit}
              onSetPrimaryScreenshot={async (stepScreenshotId) => {
                if (!selectedStep) {
                  return;
                }
                await onSetPrimaryScreenshot(selectedStep.id, stepScreenshotId);
              }}
              onRemoveScreenshot={async (stepScreenshotId) => {
                if (!selectedStep) {
                  return;
                }
                await onRemoveScreenshot(selectedStep.id, stepScreenshotId);
              }}
              onSelectCandidateScreenshot={async (step, candidate, makePrimary) => {
                await onSelectCandidateScreenshot(step.id, candidate.id, { isPrimary: makePrimary });
              }}
            />
          ) : null}

          {workspace.reviewMode === "edit" && workspace.activeEditTab === "meetings" ? (
            <section role="tabpanel" id="review-edit-panel-meetings" aria-labelledby="review-edit-tab-meetings">
              {meetingSection ?? (
                <div className="empty-state">Meeting evidence controls are not available for this session.</div>
              )}
            </section>
          ) : null}

          {workspace.reviewMode === "view" && workspace.activeViewTab === "log" ? (
            <section role="tabpanel" id="review-view-panel-log" aria-labelledby="review-view-tab-log">
              <SessionActionLogPanel entries={actionLogEntries} />
            </section>
          ) : null}
        </div>
      )}
    </section>
  );
}
