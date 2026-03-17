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
import type {
  ArtifactQueueItem,
  ArtifactUploadProgressItem,
  ArtifactUploadState,
  DiagramType,
  WorkflowContext,
} from "./types/workflow";

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
  const [sessionDetailInitialMode, setSessionDetailInitialMode] = useState<"view" | "edit">("view");
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
  const [uploadSessionId, setUploadSessionId] = useState<string | null>(null);
  const [uploadItems, setUploadItems] = useState<ArtifactUploadProgressItem[]>([]);
  const [isUploadingInputs, setIsUploadingInputs] = useState(false);

  const statusLabel = useMemo(() => {
    if (activeView === "history") {
      return "My Projects";
    }
    if (activeView === "session") {
      return "Session Detail";
    }
    return "Workspace";
  }, [activeView]);

  const requiredUploadSelected =
    uploads.videoFiles.length > 0 && uploads.transcriptFiles.length > 0 && Boolean(uploads.templateFile);
  const hasUploadedDraftReady =
    Boolean(uploadSessionId) &&
    uploadItems.length > 0 &&
    uploadItems.every((item) => item.status === "uploaded");

  const canUploadInputs = requiredUploadSelected && !isUploadingInputs && !context.isBusy;

  const canGenerateDraft =
    hasUploadedDraftReady &&
    !isUploadingInputs &&
    !context.isBusy;

  const visibleSessionHistory = useMemo(
    () => sessionHistory.filter((session) => session.status !== "draft"),
    [sessionHistory],
  );
  const resumableDraftSessions = useMemo(
    () => sessionHistory.filter((session) => session.status === "draft" && session.resumeReady && session.id !== uploadSessionId),
    [sessionHistory, uploadSessionId],
  );

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
      let nextState: ArtifactUploadState;
      if (field === "videoFiles" || field === "transcriptFiles") {
        nextState = { ...current, [field]: nextFiles };
      } else if (field === "templateFile") {
        nextState = { ...current, templateFile: nextFiles[0] ?? null };
      } else if (field === "sopFiles") {
        nextState = { ...current, optionalArtifacts: { ...current.optionalArtifacts, sopFiles: nextFiles } };
      } else {
        nextState = { ...current, optionalArtifacts: { ...current.optionalArtifacts, diagramFiles: nextFiles } };
      }

      setUploadSessionId(null);
      setUploadItems(createInitialUploadItems(nextState));
      return nextState;
    });
  }

  async function createSessionAndUploadArtifacts(): Promise<DraftSession> {
    if (uploads.videoFiles.length === 0 || uploads.transcriptFiles.length === 0 || !uploads.templateFile) {
      throw new Error("At least one video, one transcript, and one template are required.");
    }

    const session = await apiClient.createDraftSession({ title, ownerId, diagramType });
    const queue = createArtifactQueue(uploads);
    setUploadItems(createInitialUploadItems(uploads));

    for (const item of queue) {
      setUploadItems((current) =>
        current.map((entry) =>
          entry.key === item.key
            ? {
                ...entry,
                status: "uploading",
                progress: 0,
                error: null,
              }
            : entry,
        ),
      );
      try {
        await apiClient.uploadArtifactWithProgress(session.id, item.artifactKind, item.file, {
          onProgress: (progress) => {
            setUploadItems((current) =>
              current.map((entry) =>
                entry.key === item.key
                  ? {
                      ...entry,
                      status: "uploading",
                      progress,
                      error: null,
                    }
                  : entry,
              ),
            );
          },
        });
        setUploadItems((current) =>
          current.map((entry) =>
            entry.key === item.key
              ? {
                  ...entry,
                  status: "uploaded",
                  progress: 100,
                  error: null,
                }
              : entry,
          ),
        );
      } catch (error) {
        const message = getErrorMessage(error);
        setUploadItems((current) =>
          current.map((entry) =>
            entry.key === item.key
              ? {
                  ...entry,
                  status: "failed",
                  error: message,
                }
              : entry,
          ),
        );
        throw error;
      }
    }

    const refreshed = await apiClient.getDraftSession(session.id);
    setUploadSessionId(session.id);
    await loadSessionHistory();
    setContext((current) => ({
      ...current,
      currentSession: refreshed,
      selectedStepId: refreshed.processSteps[0]?.id ?? null,
      exportResult: null,
    }));
    return refreshed;
  }

  async function handleUploadInputs(): Promise<void> {
    if (!requiredUploadSelected) {
      setMessage("error", "Select at least one video, one transcript, and one DOCX template before uploading.");
      return;
    }

    setBusy(true);
    setIsUploadingInputs(true);
    try {
      await createSessionAndUploadArtifacts();
      setMessage("info", "Inputs uploaded. Click Generate Draft when you are ready to start processing.");
    } catch (error) {
      setUploadSessionId(null);
      setMessage("error", getErrorMessage(error));
    } finally {
      setIsUploadingInputs(false);
      setBusy(false);
    }
  }

  async function handleGeneratePdd(): Promise<void> {
    if (!uploadSessionId) {
      setMessage("error", "Upload the required inputs before starting draft generation.");
      return;
    }

    if (!canGenerateDraft) {
      setMessage("error", "Finish uploading the selected inputs before generating the draft.");
      return;
    }

    setBusy(true);
    try {
      const generatedSession = await apiClient.generateDraftSession(uploadSessionId);
      setSessionHistory((current) => current.filter((session) => session.id !== uploadSessionId));
      setContext((current) => ({
        ...current,
        currentSession: generatedSession,
        selectedStepId: generatedSession.processSteps[0]?.id ?? current.selectedStepId,
      }));
      setUploadSessionId(null);
      setUploadItems([]);
      setUploads(INITIAL_UPLOAD_STATE);
      setTitle("Untitled PDD Session");
      setDiagramType("flowchart");
      setActiveView("history");
      void loadSessionHistory();
      setMessage("info", "PDD generation started. Track progress in My Projects.");
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleRetrySession(sessionId: string): Promise<void> {
    setBusy(true);
    try {
      const generatedSession = await apiClient.generateDraftSession(sessionId);
      setContext((current) => ({
        ...current,
        currentSession: generatedSession,
        selectedStepId: generatedSession.processSteps[0]?.id ?? null,
      }));
      setActiveView("history");
      void loadSessionHistory();
      setMessage("info", "Draft generation retried. Track progress in My Projects.");
    } catch (error) {
      setMessage("error", getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleResumeDraft(sessionId: string): Promise<void> {
    setBusy(true);
    try {
      const session = await apiClient.getDraftSession(sessionId);
      const uploadArtifacts = session.inputArtifacts.filter((artifact) =>
        artifact.kind === "video" || artifact.kind === "transcript" || artifact.kind === "template" || artifact.kind === "sop" || artifact.kind === "diagram",
      );
      setUploadSessionId(session.id);
      setUploadItems(
        uploadArtifacts.map((artifact, index) => ({
          key: `${artifact.kind}:${artifact.id}:${index}`,
          artifactKind: artifact.kind,
          name: artifact.name,
          size: 0,
          status: "uploaded",
          progress: 100,
          error: null,
        })),
      );
      setUploads(INITIAL_UPLOAD_STATE);
      setTitle(session.title);
      setDiagramType(session.diagramType);
      setContext((current) => ({
        ...current,
        currentSession: session,
      }));
      setActiveView("workspace");
      setMessage("info", "Uploaded draft resumed. You can continue with Generate Draft.");
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
        setMessage("info", "Draft generation completed. Open the run from My Projects to review the extracted steps.");
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
                uploadItems={uploadItems}
                uploadReady={canGenerateDraft}
                disabled={context.isBusy || isUploadingInputs}
                canUploadInputs={canUploadInputs}
                canGenerateDraft={canGenerateDraft}
                showHeader={false}
                ownerLocked
                showSubmitButton={false}
                actionBar={
                  <div className="session-actions-row">
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={() => void handleUploadInputs()}
                      disabled={!canUploadInputs}
                    >
                      {isUploadingInputs ? "Uploading..." : "Upload Inputs"}
                    </button>
                    <button
                      type="button"
                      className="button-primary"
                      onClick={() => void handleGeneratePdd()}
                      disabled={!canGenerateDraft}
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
          {resumableDraftSessions.length > 0 ? (
            <section className="panel stack">
              <div className="section-header-inline">
                <div>
                  <h2>Ready To Generate</h2>
                  <p className="muted">These sessions already have uploaded inputs. Continue one to start generation without uploading again.</p>
                </div>
              </div>
              <div className="history-list">
                {resumableDraftSessions.map((session) => (
                  <div key={session.id} className="history-card">
                    <div className="history-card-main">
                      <strong>{session.title}</strong>
                      <div className="artifact-meta">
                        {session.latestStageTitle} | updated {new Date(session.updatedAt).toLocaleString()}
                      </div>
                      <div className="artifact-meta">{session.latestStageDetail}</div>
                    </div>
                    <div className="button-row">
                      <button
                        type="button"
                        className="button-primary"
                        disabled={context.isBusy}
                        onClick={() => void handleResumeDraft(session.id)}
                      >
                        Continue Draft
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </>
      ) : activeView === "history" ? (
        <SessionHistoryPage
          sessions={visibleSessionHistory}
          disabled={context.isBusy}
          onOpenView={(sessionId) => void openPastSession(sessionId, "view")}
          onOpenEdit={(sessionId) => void openPastSession(sessionId, "edit")}
          onRetry={(sessionId) => void handleRetrySession(sessionId)}
          onExportDocx={(sessionId) => void handleExportSession(sessionId, "docx")}
          onExportPdf={(sessionId) => void handleExportSession(sessionId, "pdf")}
        />
      ) : (
        <SessionDetailPage
          session={context.currentSession}
          selectedStepId={context.selectedStepId}
          initialReviewMode={sessionDetailInitialMode}
          disabled={context.isBusy}
          onBackToWorkspace={() => setActiveView("workspace")}
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
      setUploadSessionId(null);
      setUploadItems([]);
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

  async function openPastSession(sessionId: string, mode: "view" | "edit"): Promise<void> {
    setBusy(true);
    try {
      const session = await apiClient.getDraftSession(sessionId);
      setSessionDetailInitialMode(mode);
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

function createArtifactQueue(uploads: ArtifactUploadState): ArtifactQueueItem[] {
  const queue: ArtifactQueueItem[] = [
    ...uploads.videoFiles.map((file, index) => ({ key: buildArtifactQueueKey("video", file, index), artifactKind: "video" as const, file })),
    ...uploads.transcriptFiles.map((file, index) => ({
      key: buildArtifactQueueKey("transcript", file, index),
      artifactKind: "transcript" as const,
      file,
    })),
    ...(uploads.templateFile
      ? [{ key: buildArtifactQueueKey("template", uploads.templateFile, 0), artifactKind: "template" as const, file: uploads.templateFile }]
      : []),
    ...uploads.optionalArtifacts.sopFiles.map((file, index) => ({ key: buildArtifactQueueKey("sop", file, index), artifactKind: "sop" as const, file })),
    ...uploads.optionalArtifacts.diagramFiles.map((file, index) => ({
      key: buildArtifactQueueKey("diagram", file, index),
      artifactKind: "diagram" as const,
      file,
    })),
  ];

  return queue;
}

function createInitialUploadItems(uploads: ArtifactUploadState): ArtifactUploadProgressItem[] {
  return createArtifactQueue(uploads).map((item) => ({
    key: item.key,
    artifactKind: item.artifactKind,
    name: item.file.name,
    size: item.file.size,
    status: "pending",
    progress: 0,
    error: null,
  }));
}

function buildArtifactQueueKey(kind: ArtifactQueueItem["artifactKind"], file: File, index: number): string {
  return `${kind}:${file.name}:${file.size}:${file.lastModified}:${index}`;
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
