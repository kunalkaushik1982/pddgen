/**
 * Purpose: Placeholder frontend types for draft sessions and outputs.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\types\session.ts
 */

import type { ProcessNote, ProcessStep } from "./process";

export type InputArtifact = {
  id: string;
  name: string;
  kind: "video" | "transcript" | "template" | "sop" | "diagram" | "screenshot";
  storagePath: string;
};

export type OutputDocument = {
  id: string;
  kind: "docx" | "pdf";
  storagePath: string;
  exportedAt: string;
};

export type ActionLogEntry = {
  id: string;
  eventType: string;
  title: string;
  detail: string;
  actor: string;
  createdAt: string;
};

export type DraftSession = {
  id: string;
  title: string;
  status: "draft" | "processing" | "review" | "exported" | "failed";
  ownerId: string;
  diagramType: "flowchart" | "sequence";
  inputArtifacts: InputArtifact[];
  processSteps: ProcessStep[];
  processNotes: ProcessNote[];
  outputDocuments: OutputDocument[];
  actionLogs: ActionLogEntry[];
};

export type DraftSessionListItem = {
  id: string;
  title: string;
  status: DraftSession["status"];
  ownerId: string;
  diagramType: DraftSession["diagramType"];
  createdAt: string;
  updatedAt: string;
  latestStageTitle: string;
  latestStageDetail: string;
  failureDetail: string;
  resumeReady: boolean;
  canRetry: boolean;
};

export type SessionAnswerCitation = {
  id: string;
  sourceType: string;
  title: string;
  snippet: string;
};

export type SessionAnswer = {
  answer: string;
  confidence: "high" | "medium" | "low";
  citations: SessionAnswerCitation[];
};

export type ExportResult = {
  id: string;
  kind: string;
  storagePath: string;
  exportedAt: string;
};
