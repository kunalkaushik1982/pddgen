/**
 * Purpose: Shared frontend workflow types for BA state management.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\types\workflow.ts
 */

import type { DraftSession, ExportResult, InputArtifact } from "./session";

export type WorkflowMessage = {
  tone: "info" | "error";
  text: string;
};

export type WorkflowContext = {
  currentSession: DraftSession | null;
  selectedStepId: string | null;
  isBusy: boolean;
  message: WorkflowMessage | null;
  exportResult: ExportResult | null;
};

export type DiagramType = "flowchart" | "sequence";

export type ArtifactUploadState = {
  videoFiles: File[];
  transcriptFiles: File[];
  templateFile: File | null;
  optionalArtifacts: {
    sopFiles: File[];
    diagramFiles: File[];
  };
};

export type ArtifactQueueItem = {
  key: string;
  artifactKind: InputArtifact["kind"];
  file: File;
};

export type ArtifactUploadProgressStatus = "pending" | "uploading" | "uploaded" | "failed";

export type ArtifactUploadProgressItem = {
  key: string;
  artifactKind: InputArtifact["kind"];
  name: string;
  size: number;
  status: ArtifactUploadProgressStatus;
  progress: number;
  error: string | null;
};
