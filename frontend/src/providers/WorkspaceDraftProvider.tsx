import React, { createContext, useContext, useMemo, useState } from "react";

import { uiCopy } from "../constants/uiCopy";
import type { DraftSession } from "../types/session";
import type {
  ArtifactQueueItem,
  ArtifactUploadProgressItem,
  ArtifactUploadState,
  DiagramType,
} from "../types/workflow";

const INITIAL_UPLOAD_STATE: ArtifactUploadState = {
  videoFiles: [],
  transcriptFiles: [],
  templateFile: null,
  optionalArtifacts: {
    sopFiles: [],
    diagramFiles: [],
  },
};

type WorkspaceDraftContextValue = {
  title: string;
  ownerId: string;
  diagramType: DiagramType;
  uploads: ArtifactUploadState;
  uploadSessionId: string | null;
  uploadItems: ArtifactUploadProgressItem[];
  setTitle: (value: string) => void;
  setOwnerId: (value: string) => void;
  setDiagramType: (value: DiagramType) => void;
  updateFiles: (field: keyof ArtifactUploadState | "sopFiles" | "diagramFiles", files: FileList | null) => void;
  setUploadSessionId: (value: string | null) => void;
  setUploadItems: React.Dispatch<React.SetStateAction<ArtifactUploadProgressItem[]>>;
  hydrateFromDraftSession: (session: DraftSession) => void;
  reset: () => void;
};

const WorkspaceDraftContext = createContext<WorkspaceDraftContextValue | null>(null);

export function WorkspaceDraftProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [title, setTitle] = useState<string>(uiCopy.defaultDraftTitle);
  const [ownerId, setOwnerId] = useState("");
  const [diagramType, setDiagramType] = useState<DiagramType>("flowchart");
  const [uploads, setUploads] = useState<ArtifactUploadState>(INITIAL_UPLOAD_STATE);
  const [uploadSessionId, setUploadSessionId] = useState<string | null>(null);
  const [uploadItems, setUploadItems] = useState<ArtifactUploadProgressItem[]>([]);

  function updateFiles(field: keyof ArtifactUploadState | "sopFiles" | "diagramFiles", files: FileList | null): void {
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
    setUploadSessionId(null);
    setUploadItems((current) => (current.length > 0 ? [] : current));
  }

  function hydrateFromDraftSession(session: DraftSession): void {
    const uploadArtifacts = session.inputArtifacts.filter((artifact) =>
      artifact.kind === "video" || artifact.kind === "transcript" || artifact.kind === "template" || artifact.kind === "sop" || artifact.kind === "diagram",
    );
    setTitle(session.title);
    setOwnerId(session.ownerId);
    setDiagramType(session.diagramType);
    setUploadSessionId(session.id);
    setUploads(INITIAL_UPLOAD_STATE);
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
  }

  function reset(): void {
    setTitle(uiCopy.defaultDraftTitle);
    setOwnerId("");
    setDiagramType("flowchart");
    setUploads(INITIAL_UPLOAD_STATE);
    setUploadSessionId(null);
    setUploadItems([]);
  }

  const value = useMemo<WorkspaceDraftContextValue>(
    () => ({
      title,
      ownerId,
      diagramType,
      uploads,
      uploadSessionId,
      uploadItems,
      setTitle,
      setOwnerId,
      setDiagramType,
      updateFiles,
      setUploadSessionId,
      setUploadItems,
      hydrateFromDraftSession,
      reset,
    }),
    [diagramType, ownerId, title, uploadItems, uploadSessionId, uploads],
  );

  return <WorkspaceDraftContext.Provider value={value}>{children}</WorkspaceDraftContext.Provider>;
}

export function useWorkspaceDraft(): WorkspaceDraftContextValue {
  const context = useContext(WorkspaceDraftContext);
  if (!context) {
    throw new Error("useWorkspaceDraft must be used within WorkspaceDraftProvider.");
  }
  return context;
}

export function createArtifactQueue(uploads: ArtifactUploadState): ArtifactQueueItem[] {
  return [
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
}

export function createInitialUploadItems(uploads: ArtifactUploadState): ArtifactUploadProgressItem[] {
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
