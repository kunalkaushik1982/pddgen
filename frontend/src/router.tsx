/**
 * Purpose: Orchestrate the BA workflow views within a single workspace page.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\router.tsx
 */

import React, { useEffect, useMemo, useState } from "react";

import { AppShell } from "./components/layout/AppShell";
import { AuthPage } from "./pages/AuthPage";
import { SessionDetailPage } from "./pages/SessionDetailPage";
import { SessionHistoryPage } from "./pages/SessionHistoryPage";
import { UploadPage } from "./pages/UploadPage";
import { apiClient } from "./services/apiClient";
import type { User } from "./types/auth";
import type { ProcessStep } from "./types/process";
import type { DraftSession, DraftSessionListItem } from "./types/session";
import type { ArtifactQueueItem, ArtifactUploadState, DiagramType, WorkflowContext } from "./types/workflow";

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
  const [diagramType, setDiagramType] = useState<DiagramType>("flowchart");
  const [uploads, setUploads] = useState<ArtifactUploadState>(INITIAL_UPLOAD_STATE);
  const [context, setContext] = useState<WorkflowContext>(INITIAL_WORKFLOW_CONTEXT);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeView, setActiveView] = useState<"workspace" | "history" | "session">("workspace");
  const [sessionHistory, setSessionHistory] = useState<DraftSessionListItem[]>([]);
  const [collapsedSections, setCollapsedSections] = useState({
    controls: false,
    review: false,
  });

  const statusLabel = useMemo(() => {
    if (activeView === "history") {
      return "Past Runs";
    }
    if (activeView === "session") {
      return "Session Detail";
    }
    return "Workspace";
  }, [activeView]);

  const canGenerateDraft =
    uploads.videoFiles.length > 0 && uploads.transcriptFiles.length > 0 && Boolean(uploads.templateFile);

  useEffect(() => {
    void restoreUser();
  }, []);

  useEffect(() => {
    if (!currentUser) {
      return;
    }
    setOwnerId(currentUser.username);
    void loadSessionHistory();
  }, [currentUser?.id]);

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

  useEffect(() => {
    if (!currentUser || !sessionHistory.some((session) => session.status === "processing")) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      void loadSessionHistory();
    }, 5000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [currentUser?.id, sessionHistory]);

  function setMessage(tone: "info" | "error", text: string): void {
    setContext((current) => ({
      ...current,
      message: { tone, text },
    }));
  }

  function setBusy(isBusy: boolean): void {
    setContext((current) => ({ ...current, isBusy }));
  }

  function toggleSection(section: keyof typeof collapsedSections): void {
    setCollapsedSections((current) => ({
      ...current,
      [section]: !current[section],
    }));
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

  async function createSessionAndUploadArtifacts(): Promise<DraftSession> {
    if (uploads.videoFiles.length === 0 || uploads.transcriptFiles.length === 0 || !uploads.templateFile) {
      throw new Error("At least one video, one transcript, and one template are required.");
    }

    const session = await apiClient.createDraftSession({ title, ownerId, diagramType });
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
    await loadSessionHistory();
    setContext((current) => ({
      ...current,
      currentSession: refreshed,
      selectedStepId: refreshed.processSteps[0]?.id ?? null,
      exportResult: null,
    }));
    return refreshed;
  }

  async function handleGeneratePdd(): Promise<void> {
    if (!canGenerateDraft) {
      setMessage("error", "Select at least one video, one transcript, and one DOCX template before generating the draft.");
      return;
    }

    setBusy(true);
    try {
      const uploadedSession = await createSessionAndUploadArtifacts();
      const generatedSession = await apiClient.generateDraftSession(uploadedSession.id);
      setContext((current) => ({
        ...current,
        currentSession: generatedSession,
        selectedStepId: generatedSession.processSteps[0]?.id ?? current.selectedStepId,
      }));
      setUploads(INITIAL_UPLOAD_STATE);
      setTitle("Untitled PDD Session");
      setDiagramType("flowchart");
      await loadSessionHistory();
      setActiveView("history");
      setMessage("info", "PDD generation started. Track progress in Past Runs.");
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
        void loadSessionHistory();
        setMessage("info", "Draft generation completed. Open the run from Past Runs to review the extracted steps.");
      }
      if (session.status === "failed") {
        void loadSessionHistory();
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
      await apiClient.updateProcessStep(context.currentSession.id, stepId, payload);
      const updatedSession = await apiClient.getDraftSession(context.currentSession.id);
      const updatedStep = updatedSession.processSteps.find((step) => step.id === stepId) ?? updatedSession.processSteps[0];
      setContext((current) => ({
        ...current,
        currentSession: updatedSession,
        selectedStepId: updatedStep?.id ?? current.selectedStepId,
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
      await apiClient.updateStepScreenshot(context.currentSession.id, stepId, stepScreenshotId, {
        isPrimary: true,
      });
      const updatedSession = await apiClient.getDraftSession(context.currentSession.id);
      const updatedStep = updatedSession.processSteps.find((step) => step.id === stepId) ?? updatedSession.processSteps[0];
      setContext((current) => ({
        ...current,
        currentSession: updatedSession,
        selectedStepId: updatedStep?.id ?? current.selectedStepId,
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
      await apiClient.deleteStepScreenshot(context.currentSession.id, stepId, stepScreenshotId);
      const updatedSession = await apiClient.getDraftSession(context.currentSession.id);
      const updatedStep = updatedSession.processSteps.find((step) => step.id === stepId) ?? updatedSession.processSteps[0];
      setContext((current) => ({
        ...current,
        currentSession: updatedSession,
        selectedStepId: updatedStep?.id ?? current.selectedStepId,
      }));
      setMessage("info", "Screenshot removed from the step.");
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleSelectCandidateScreenshot(
    stepId: string,
    candidateScreenshotId: string,
    payload: { isPrimary?: boolean; role?: string } = {},
  ): Promise<void> {
    if (!context.currentSession) {
      return;
    }

    setBusy(true);
    try {
      await apiClient.selectCandidateScreenshot(
        context.currentSession.id,
        stepId,
        candidateScreenshotId,
        payload,
      );
      const updatedSession = await apiClient.getDraftSession(context.currentSession.id);
      const updatedStep = updatedSession.processSteps.find((step) => step.id === stepId) ?? updatedSession.processSteps[0];
      setContext((current) => ({
        ...current,
        currentSession: updatedSession,
        selectedStepId: updatedStep?.id ?? current.selectedStepId,
      }));
      setMessage("info", "Screenshot selection updated.");
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
      await loadSessionHistory();
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

  async function handleExportSession(sessionId: string, format: "docx" | "pdf"): Promise<void> {
    setBusy(true);
    try {
      if (format === "pdf") {
        await apiClient.downloadExportPdf(sessionId);
      } else {
        await apiClient.downloadExportDocx(sessionId);
      }
      const refreshed = await apiClient.getDraftSession(sessionId);
      await loadSessionHistory();
      setContext((current) => ({
        ...current,
        currentSession: refreshed,
        selectedStepId: refreshed.processSteps[0]?.id ?? null,
        exportResult: refreshed.outputDocuments[0]
          ? {
              id: refreshed.outputDocuments[0].id,
              kind: refreshed.outputDocuments[0].kind,
              storagePath: refreshed.outputDocuments[0].storagePath,
              exportedAt: refreshed.outputDocuments[0].exportedAt,
            }
          : current.exportResult,
      }));
      setMessage("info", `${format.toUpperCase()} downloaded.`);
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  if (!currentUser) {
    return (
      <AuthPage
        disabled={context.isBusy}
        message={context.message}
        onLogin={handleLogin}
        onRegister={handleRegister}
      />
    );
  }

  return (
    <AppShell
      title="PDD Generator"
      subtitle="Upload discovery evidence, review AI-drafted AS-IS steps, and export a DOCX PDD."
      statusLabel={statusLabel}
      userLabel={currentUser.username}
      activeView={activeView}
      onSelectView={setActiveView}
      onLogout={() => void handleLogout()}
    >
      {context.message ? <div className={`status-banner ${context.message.tone === "error" ? "error" : ""}`}>{context.message.text}</div> : null}

      {activeView === "workspace" ? (
        <>
          <div className="session-controls-section">
            <CollapsibleSection
              title="1. Session Controls"
              description="Upload evidence, generate the PDD draft, and export the DOCX from one compact panel."
              collapsed={collapsedSections.controls}
              onToggle={() => toggleSection("controls")}
            >
              <UploadPage
                title={title}
                ownerId={ownerId}
                diagramType={diagramType}
                uploads={uploads}
                disabled={context.isBusy}
                showHeader={false}
                ownerLocked
                showSubmitButton={false}
                actionBar={
                  <div className="session-actions-row">
                    <button
                      type="button"
                      className="button-primary"
                      onClick={() => void handleGeneratePdd()}
                      disabled={context.isBusy || !canGenerateDraft}
                    >
                      Generate Draft
                    </button>
                  </div>
                }
                onTitleChange={setTitle}
                onOwnerIdChange={setOwnerId}
                onDiagramTypeChange={setDiagramType}
                onFilesChange={handleFilesChange}
                onSubmit={() => void handleGeneratePdd()}
              />
            </CollapsibleSection>
          </div>
        </>
      ) : activeView === "history" ? (
        <SessionHistoryPage
          sessions={sessionHistory}
          disabled={context.isBusy}
          onRefresh={() => void loadSessionHistory()}
          onOpen={(sessionId) => void openPastSession(sessionId)}
          onExportDocx={(sessionId) => void handleExportSession(sessionId, "docx")}
          onExportPdf={(sessionId) => void handleExportSession(sessionId, "pdf")}
        />
      ) : (
        <SessionDetailPage
          session={context.currentSession}
          selectedStepId={context.selectedStepId}
          disabled={context.isBusy}
          onBackToWorkspace={() => setActiveView("workspace")}
          onRefresh={() => void handleRefreshSession()}
          onExportDocx={() => context.currentSession ? void handleExportSession(context.currentSession.id, "docx") : undefined}
          onExportPdf={() => context.currentSession ? void handleExportSession(context.currentSession.id, "pdf") : undefined}
          onSelectStep={(stepId) => setContext((current) => ({ ...current, selectedStepId: stepId }))}
          onSaveStep={handleSaveStep}
          onSetPrimaryScreenshot={handleSetPrimaryScreenshot}
          onRemoveScreenshot={handleRemoveScreenshot}
          onRefreshSession={() => handleRefreshSession()}
          onSelectCandidateScreenshot={handleSelectCandidateScreenshot}
        />
      )}
    </AppShell>
  );

  async function restoreUser(): Promise<void> {
    try {
      const user = await apiClient.getCurrentUser();
      setCurrentUser(user);
      setOwnerId(user.username);
    } catch {
      apiClient.clearAuthToken();
      setCurrentUser(null);
    }
  }

  async function handleLogin(username: string, password: string): Promise<void> {
    setBusy(true);
    try {
      const user = await apiClient.login(username, password);
      setCurrentUser(user);
      setOwnerId(user.username);
      setMessage("info", `Signed in as ${user.username}.`);
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleRegister(username: string, password: string): Promise<void> {
    setBusy(true);
    try {
      const user = await apiClient.register(username, password);
      setCurrentUser(user);
      setOwnerId(user.username);
      setMessage("info", `Account created for ${user.username}.`);
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleLogout(): Promise<void> {
    setBusy(true);
    try {
      await apiClient.logout();
    } finally {
      setCurrentUser(null);
      setSessionHistory([]);
      setContext(INITIAL_WORKFLOW_CONTEXT);
      setUploads(INITIAL_UPLOAD_STATE);
      setActiveView("workspace");
      setOwnerId("pilot-user");
      setDiagramType("flowchart");
      setBusy(false);
    }
  }

  async function loadSessionHistory(): Promise<void> {
    try {
      const sessions = await apiClient.listDraftSessions();
      setSessionHistory(sessions);
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    }
  }

  async function openPastSession(sessionId: string): Promise<void> {
    setBusy(true);
    try {
      const session = await apiClient.getDraftSession(sessionId);
      setContext((current) => ({
        ...current,
        currentSession: session,
        selectedStepId: session.processSteps[0]?.id ?? null,
      }));
      setActiveView("session");
      setMessage("info", `Loaded session ${session.title}.`);
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "An unexpected error occurred.";
}

type CollapsibleSectionProps = {
  title: string;
  description: string;
  collapsed: boolean;
  onToggle: () => void;
  children: React.ReactNode;
};

function CollapsibleSection({
  title,
  description,
  collapsed,
  onToggle,
  children,
}: CollapsibleSectionProps): JSX.Element {
  return (
    <section className="collapsible-section">
      <div className="collapsible-header">
        <div>
          <h2>{title}</h2>
          {!collapsed ? <p className="muted">{description}</p> : null}
        </div>
        <button type="button" className="button-secondary collapsible-toggle" onClick={onToggle}>
          {collapsed ? "Expand" : "Collapse"}
        </button>
      </div>
      {!collapsed ? children : null}
    </section>
  );
}
