/**
 * Purpose: Orchestrate the BA workflow views within a single workspace page.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\router.tsx
 */

import React, { useEffect, useMemo, useState } from "react";

import { AppShell } from "./components/layout/AppShell";
import { ExportPage } from "./pages/ExportPage";
import { ProcessingPage } from "./pages/ProcessingPage";
import { StepReviewPage } from "./pages/StepReviewPage";
import { UploadPage } from "./pages/UploadPage";
import { apiClient } from "./services/apiClient";
import type { ProcessStep } from "./types/process";
import type { DraftSession } from "./types/session";
import type { ArtifactQueueItem, ArtifactUploadState, WorkflowContext } from "./types/workflow";

const INITIAL_UPLOAD_STATE: ArtifactUploadState = {
  videoFiles: [],
  transcriptFiles: [],
  templateFile: null,
  optionalArtifacts: {
    sopFiles: [],
    diagramFiles: [],
  },
};

const INITIAL_WORKFLOW_CONTEXT: WorkflowContext = {
  currentSession: null,
  selectedStepId: null,
  isBusy: false,
  message: null,
  exportResult: null,
};

export function AppRouter(): JSX.Element {
  const [title, setTitle] = useState("Untitled PDD Session");
  const [ownerId, setOwnerId] = useState("pilot-user");
  const [uploads, setUploads] = useState<ArtifactUploadState>(INITIAL_UPLOAD_STATE);
  const [context, setContext] = useState<WorkflowContext>(INITIAL_WORKFLOW_CONTEXT);

  const statusLabel = useMemo(() => {
    if (!context.currentSession) {
      return "No active session";
    }
    return `${context.currentSession.status.toUpperCase()} | ${context.currentSession.processSteps.length} step(s)`;
  }, [context.currentSession]);

  useEffect(() => {
    if (!context.currentSession || context.currentSession.status !== "processing") {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      void pollSession(context.currentSession!.id);
    }, 5000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [context.currentSession?.id, context.currentSession?.status]);

  function setMessage(tone: "info" | "error", text: string): void {
    setContext((current) => ({
      ...current,
      message: { tone, text },
    }));
  }

  function setBusy(isBusy: boolean): void {
    setContext((current) => ({ ...current, isBusy }));
  }

  function handleFilesChange(field: keyof ArtifactUploadState | "sopFiles" | "diagramFiles", files: FileList | null): void {
    const nextFiles = files ? Array.from(files) : [];
    setUploads((current) => {
      if (field === "videoFiles" || field === "transcriptFiles") {
        return { ...current, [field]: nextFiles };
      }
      if (field === "templateFile") {
        return { ...current, templateFile: nextFiles[0] ?? null };
      }
      if (field === "sopFiles") {
        return { ...current, optionalArtifacts: { ...current.optionalArtifacts, sopFiles: nextFiles } };
      }
      return { ...current, optionalArtifacts: { ...current.optionalArtifacts, diagramFiles: nextFiles } };
    });
  }

  async function handleCreateSessionAndUpload(): Promise<void> {
    if (uploads.videoFiles.length === 0 || uploads.transcriptFiles.length === 0 || !uploads.templateFile) {
      setMessage("error", "At least one video, one transcript, and one template are required.");
      return;
    }

    setBusy(true);
    try {
      const session = await apiClient.createDraftSession({ title, ownerId });
      const queue: ArtifactQueueItem[] = [
        ...uploads.videoFiles.map((file) => ({ artifactKind: "video" as const, file })),
        ...uploads.transcriptFiles.map((file) => ({ artifactKind: "transcript" as const, file })),
        { artifactKind: "template" as const, file: uploads.templateFile },
        ...uploads.optionalArtifacts.sopFiles.map((file) => ({ artifactKind: "sop" as const, file })),
        ...uploads.optionalArtifacts.diagramFiles.map((file) => ({ artifactKind: "diagram" as const, file })),
      ];

      for (const item of queue) {
        await apiClient.uploadArtifact(session.id, item.artifactKind, item.file);
      }

      const refreshed = await apiClient.getDraftSession(session.id);
      setContext((current) => ({
        ...current,
        currentSession: refreshed,
        selectedStepId: refreshed.processSteps[0]?.id ?? null,
        exportResult: null,
      }));
      setMessage("info", "Session created and all selected artifacts uploaded.");
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleGenerateDraft(): Promise<void> {
    if (!context.currentSession) {
      return;
    }

    setBusy(true);
    try {
      const session = await apiClient.generateDraftSession(context.currentSession.id);
      setContext((current) => ({
        ...current,
        currentSession: session,
        selectedStepId: current.selectedStepId,
      }));
      setMessage("info", "Draft generation queued. The session will refresh automatically while processing.");
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function pollSession(sessionId: string): Promise<void> {
    try {
      const session = await apiClient.getDraftSession(sessionId);
      setContext((current) => ({
        ...current,
        currentSession: session,
        selectedStepId:
          current.selectedStepId && session.processSteps.some((step) => step.id === current.selectedStepId)
            ? current.selectedStepId
            : session.processSteps[0]?.id ?? null,
      }));

      if (session.status === "review") {
        setMessage("info", "Draft generation completed. Review the extracted steps before export.");
      }
      if (session.status === "failed") {
        setMessage("error", "Draft generation failed. Check worker logs and try again.");
      }
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    }
  }

  async function handleRefreshSession(): Promise<void> {
    if (!context.currentSession) {
      return;
    }

    setBusy(true);
    try {
      const session = await apiClient.getDraftSession(context.currentSession.id);
      setContext((current) => ({
        ...current,
        currentSession: session,
        selectedStepId: current.selectedStepId ?? session.processSteps[0]?.id ?? null,
      }));
      setMessage("info", "Session refreshed.");
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveStep(stepId: string, payload: Partial<ProcessStep>): Promise<void> {
    if (!context.currentSession) {
      return;
    }

    setBusy(true);
    try {
      const updatedStep = await apiClient.updateProcessStep(context.currentSession.id, stepId, payload);
      const updatedSession = replaceStep(context.currentSession, updatedStep);
      setContext((current) => ({
        ...current,
        currentSession: updatedSession,
        selectedStepId: updatedStep.id,
      }));
      setMessage("info", "Step changes saved.");
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleSetPrimaryScreenshot(stepId: string, stepScreenshotId: string): Promise<void> {
    if (!context.currentSession) {
      return;
    }

    setBusy(true);
    try {
      const updatedStep = await apiClient.updateStepScreenshot(context.currentSession.id, stepId, stepScreenshotId, {
        isPrimary: true,
      });
      const updatedSession = replaceStep(context.currentSession, updatedStep);
      setContext((current) => ({
        ...current,
        currentSession: updatedSession,
        selectedStepId: updatedStep.id,
      }));
      setMessage("info", "Primary screenshot updated.");
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleRemoveScreenshot(stepId: string, stepScreenshotId: string): Promise<void> {
    if (!context.currentSession) {
      return;
    }

    setBusy(true);
    try {
      const updatedStep = await apiClient.deleteStepScreenshot(context.currentSession.id, stepId, stepScreenshotId);
      const updatedSession = replaceStep(context.currentSession, updatedStep);
      setContext((current) => ({
        ...current,
        currentSession: updatedSession,
        selectedStepId: updatedStep.id,
      }));
      setMessage("info", "Screenshot removed from the step.");
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleExport(): Promise<void> {
    if (!context.currentSession) {
      return;
    }

    setBusy(true);
    try {
      const exportResult = await apiClient.exportDocx(context.currentSession.id);
      const refreshed = await apiClient.getDraftSession(context.currentSession.id);
      setContext((current) => ({
        ...current,
        currentSession: refreshed,
        exportResult,
      }));
      setMessage("info", "DOCX export completed.");
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell
      title="PDD Generator"
      subtitle="Upload discovery evidence, review AI-drafted AS-IS steps, and export a DOCX PDD."
      statusLabel={statusLabel}
    >
      {context.message ? <div className={`status-banner ${context.message.tone === "error" ? "error" : ""}`}>{context.message.text}</div> : null}

      <div className="workflow-grid">
        <div className="stack">
          <UploadPage
            title={title}
            ownerId={ownerId}
            uploads={uploads}
            disabled={context.isBusy}
            onTitleChange={setTitle}
            onOwnerIdChange={setOwnerId}
            onFilesChange={handleFilesChange}
            onSubmit={() => void handleCreateSessionAndUpload()}
          />
          <StepReviewPage
            session={context.currentSession}
            selectedStepId={context.selectedStepId}
            disabled={context.isBusy}
            onSelectStep={(stepId) => setContext((current) => ({ ...current, selectedStepId: stepId }))}
            onSaveStep={handleSaveStep}
            onSetPrimaryScreenshot={handleSetPrimaryScreenshot}
            onRemoveScreenshot={handleRemoveScreenshot}
          />
        </div>

        <div className="stack">
          <ProcessingPage
            session={context.currentSession}
            disabled={context.isBusy}
            onGenerate={() => void handleGenerateDraft()}
            onRefresh={() => void handleRefreshSession()}
          />
          <SessionArtifactsPanel session={context.currentSession} />
          <ExportPage
            session={context.currentSession}
            exportResult={context.exportResult}
            disabled={context.isBusy}
            onExport={() => void handleExport()}
          />
        </div>
      </div>
    </AppShell>
  );
}

type SessionArtifactsPanelProps = {
  session: DraftSession | null;
};

function SessionArtifactsPanel({ session }: SessionArtifactsPanelProps): JSX.Element {
  return (
    <section className="panel stack">
      <div>
        <h2>Session Artifacts</h2>
        <p className="muted">Track uploaded source files and derived screenshots.</p>
      </div>

      {session ? (
        <div className="artifact-list">
          {session.inputArtifacts.map((artifact) => (
            <div key={artifact.id} className="artifact-card">
              <strong>{artifact.name}</strong>
              <div className="artifact-meta">
                {artifact.kind} | {artifact.storagePath}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">Artifacts will appear here once the session is created.</div>
      )}
    </section>
  );
}

function replaceStep(session: DraftSession, updatedStep: ProcessStep): DraftSession {
  return {
    ...session,
    processSteps: session.processSteps.map((step) => (step.id === updatedStep.id ? updatedStep : step)),
  };
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "An unexpected error occurred.";
}
