/**
 * Purpose: Step review page for moderate BA edits.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\StepReviewPage.tsx
 */

import React, { Suspense, lazy } from "react";

import { ReviewWorkspaceTabs } from "../components/review/ReviewWorkspaceTabs";
import { uiCopy } from "../constants/uiCopy";
import { SessionActionLogPanel } from "../components/review/SessionActionLogPanel";
import { SessionArtifactsPanel } from "../components/review/SessionArtifactsPanel";
import { DocumentSectionProcessSection } from "../components/review/DocumentSectionProcessSection";
import { SessionDiagramSection } from "../components/review/SessionDiagramSection";
import { SessionProcessSection } from "../components/review/SessionProcessSection";
import { SessionSummaryPanel } from "../components/review/SessionSummaryPanel";
import { useAskSession } from "../hooks/useAskSession";
import { useReviewWorkspace, type ReviewMode } from "../hooks/useReviewWorkspace";
import { useStepEditor } from "../hooks/useStepEditor";
import type { ProcessStep } from "../types/process";
import type { DraftSession } from "../types/session";
import { formatGenerationTimeSummary } from "../utils/formatWallDuration";

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
  const usesExportSectionProcess = session.documentType === "brd" || session.documentType === "sop";
  const enrichmentFieldsMerged = React.useMemo(() => {
    const raw = session.exportTextEnrichment?.fields ?? {};
    const out: Record<string, string> = {};
    for (const id of session.enrichmentFieldIds) {
      out[id] = raw[id] ?? "";
    }
    return out;
  }, [session.exportTextEnrichment, session.enrichmentFieldIds]);
  const showProcessStepsEmpty = !usesExportSectionProcess && session.processSteps.length === 0;
  const sortedProcessGroups = React.useMemo(
    () => [...session.processGroups].sort((left, right) => left.displayOrder - right.displayOrder),
    [session.processGroups],
  );
  const firstProcessGroupId = sortedProcessGroups[0]?.id ?? null;
  const stepCountByProcessGroup = React.useMemo(() => {
    const counts = new Map<string, number>();
    for (const step of session.processSteps) {
      if (step.processGroupId) {
        counts.set(step.processGroupId, (counts.get(step.processGroupId) ?? 0) + 1);
      }
    }
    const orphanCount = session.processSteps.filter((row) => !row.processGroupId).length;
    if (orphanCount > 0 && firstProcessGroupId) {
      counts.set(firstProcessGroupId, (counts.get(firstProcessGroupId) ?? 0) + orphanCount);
    }
    return counts;
  }, [session.processSteps, firstProcessGroupId]);
  const availableProcessGroups = sortedProcessGroups.filter((group) => {
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
    ? session.processSteps.filter((step) => {
        const groupId = step.processGroupId ?? null;
        if (groupId === activeProcessGroup.id) {
          return true;
        }
        if (!groupId && firstProcessGroupId === activeProcessGroup.id) {
          return true;
        }
        return false;
      })
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
  const countStepScreenshotEvidence = (step: ProcessStep): number =>
    step.screenshots.length > 0 ? step.screenshots.length : step.candidateScreenshots.length;
  const screenshotCount = filteredSteps.reduce((total, step) => total + countStepScreenshotEvidence(step), 0);
  const primaryScreenshotCount = filteredSteps.reduce(
    (total, step) =>
      total +
      (step.screenshots.length > 0
        ? step.screenshots.filter((screenshot) => screenshot.isPrimary).length
        : step.candidateScreenshots.length > 0
          ? 1
          : 0),
    0,
  );
  const summaryHeading = activeProcessGroup?.title || filteredNotes[0]?.text || uiCopy.summaryHeadingFallback;
  const summarySubheading = applications.length > 0 ? applications.join(" and ") : uiCopy.summarySubheadingFallback;
  const summaryBullets = filteredSteps.map((step) => step.actionText);
  const summarySteps = activeProcessGroup ? filteredSteps : session.processSteps;
  const summaryNotes = activeProcessGroup ? filteredNotes : session.processNotes;
  const summaryApplications = Array.from(new Set(summarySteps.map((step) => step.applicationName).filter(Boolean)));
  const summaryEditedSteps = summarySteps.filter((step) => step.editedByBa);
  const summaryScreenshotCount = summarySteps.reduce((total, step) => total + countStepScreenshotEvidence(step), 0);
  const summaryPrimaryScreenshotCount = summarySteps.reduce(
    (total, step) =>
      total +
      (step.screenshots.length > 0
        ? step.screenshots.filter((screenshot) => screenshot.isPrimary).length
        : step.candidateScreenshots.length > 0
          ? 1
          : 0),
    0,
  );
  const summaryPanelHeading = activeProcessGroup?.title || summaryNotes[0]?.text || uiCopy.summaryHeadingFallback;
  const summaryPanelSubheading =
    summaryApplications.length > 0 ? summaryApplications.join(" and ") : uiCopy.summarySubheadingFallback;
  const summaryNarrative =
    (activeProcessGroup?.summaryText ?? "").trim() ||
    (availableProcessGroups.length === 1 ? (availableProcessGroups[0]?.summaryText ?? "").trim() : "");
  const summaryBulletsForPanel = summarySteps.map((step) => step.actionText);
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
          {formatGenerationTimeSummary(session) ? (
            <div className="artifact-meta">Generation time: {formatGenerationTimeSummary(session)}</div>
          ) : null}
        </div>
          <div className="review-header-actions">
          <div
            className={`review-header-action-slot review-header-action-slot-${workspace.reviewMode} review-header-action-slot-edit-${workspace.activeEditTab}`}
          >
            {headerActions}
          </div>
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
            <button
              type="button"
              role="tab"
              aria-selected={workspace.reviewMode === "artifacts"}
              className={`review-mode-tab ${workspace.reviewMode === "artifacts" ? "review-mode-tab-active" : ""}`}
              onClick={() => workspace.switchMode("artifacts")}
            >
              Artifacts
            </button>
          </div>
          {onCloseSession ? (
            <button type="button" className="button-secondary" onClick={onCloseSession} disabled={disabled}>
              Close session
            </button>
          ) : null}
        </div>
      </div>

      {workspace.reviewMode === "artifacts" && session.inputArtifacts.length > 0 ? (
        <SessionArtifactsPanel artifacts={session.inputArtifacts} />
      ) : null}

      {workspace.reviewMode !== "artifacts" && showProcessStepsEmpty ? (
        <div className="empty-state">No steps have been generated yet.</div>
      ) : workspace.reviewMode !== "artifacts" ? (
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
                    title={group.title}
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
                heading={summaryPanelHeading}
                subheading={summaryPanelSubheading}
                narrativeText={summaryNarrative}
                summaryBullets={summaryBulletsForPanel}
                sessionTitle={session.title}
                stepCount={summarySteps.length}
                diagramType={session.diagramType}
                applicationsLabel={summaryApplications.length > 0 ? summaryApplications.join(", ") : "Not detected"}
                applicationCount={summaryApplications.length}
                screenshotCount={summaryScreenshotCount}
                primaryScreenshotCount={summaryPrimaryScreenshotCount}
                editedStepCount={summaryEditedSteps.length}
                noteCount={summaryNotes.length}
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
            usesExportSectionProcess ? (
              <DocumentSectionProcessSection
                sessionId={session.id}
                documentLabel={session.documentType.toUpperCase()}
                fieldIds={session.enrichmentFieldIds}
                fields={enrichmentFieldsMerged}
                mode="view"
                disabled={disabled}
              />
            ) : (
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
            )
          ) : null}

          {workspace.reviewMode === "edit" && workspace.activeEditTab === "steps" ? (
            usesExportSectionProcess ? (
              <DocumentSectionProcessSection
                sessionId={session.id}
                documentLabel={session.documentType.toUpperCase()}
                fieldIds={session.enrichmentFieldIds}
                fields={enrichmentFieldsMerged}
                mode="edit"
                disabled={disabled}
                onAfterSave={onRefreshSession}
              />
            ) : (
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
            )
          ) : null}

          {workspace.reviewMode === "view" && workspace.activeViewTab === "log" ? (
            <section role="tabpanel" id="review-view-panel-log" aria-labelledby="review-view-tab-log">
              <SessionActionLogPanel entries={actionLogEntries} />
            </section>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
