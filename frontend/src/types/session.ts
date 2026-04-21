/**
 * Purpose: Placeholder frontend types for draft sessions and outputs.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\types\session.ts
 */

import type { ProcessNote, ProcessStep } from "./process";

export type DocumentType = "pdd" | "sop" | "brd";

export type ProcessGroup = {
  id: string;
  sessionId: string;
  title: string;
  canonicalSlug: string;
  status: string;
  displayOrder: number;
  summaryText: string;
  capabilityTags: string[];
  overviewDiagramJson: string;
  detailedDiagramJson: string;
};

export type InputArtifact = {
  id: string;
  meetingId?: string | null;
  uploadBatchId?: string | null;
  uploadPairIndex?: number | null;
  name: string;
  kind: "video" | "transcript" | "template" | "sop" | "diagram" | "screenshot";
  storagePath: string;
  contentType?: string | null;
  previewUrl?: string | null;
  previewExpiresAt?: string | null;
  sizeBytes?: number;
  createdAt?: string | null;
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
  metadata: Record<string, unknown>;
  actor: string;
  createdAt: string;
};

export type PendingEvidenceBundle = {
  id: string;
  meetingId: string;
  meetingTitle: string;
  uploadedAt: string;
  pairIndex: number;
  transcriptArtifactId?: string | null;
  transcriptName?: string | null;
  videoArtifactId?: string | null;
  videoName?: string | null;
};

export type ExportTextEnrichment = {
  version: number;
  fields: Record<string, string>;
};

export type TokenUsageBucket = {
  key: string;
  calls: number;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
};

export type TokenUsageRun = {
  runNumber: number;
  startedAt: string;
  endedAt?: string | null;
  calls: number;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
};

export type SessionTokenUsage = {
  calls: number;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  byModel: TokenUsageBucket[];
  bySkill: TokenUsageBucket[];
  byRun: TokenUsageRun[];
};

export type DraftSession = {
  id: string;
  title: string;
  status: "draft" | "processing" | "review" | "exported" | "failed";
  ownerId: string;
  diagramType: "flowchart" | "sequence";
  documentType: DocumentType;
  draftGenerationStartedAt?: string | null;
  draftGenerationCompletedAt?: string | null;
  screenshotGenerationStartedAt?: string | null;
  screenshotGenerationCompletedAt?: string | null;
  draftGenerationDurationSeconds?: number | null;
  screenshotGenerationDurationSeconds?: number | null;
  hasUnprocessedEvidence: boolean;
  pendingEvidenceBundles: PendingEvidenceBundle[];
  processGroups: ProcessGroup[];
  inputArtifacts: InputArtifact[];
  processSteps: ProcessStep[];
  processNotes: ProcessNote[];
  outputDocuments: OutputDocument[];
  actionLogs: ActionLogEntry[];
  /** Batched export placeholder bodies (AI + BA edits); merged into DOCX/PDF. */
  exportTextEnrichment: ExportTextEnrichment | null;
  tokenUsage: SessionTokenUsage;
  /** Ordered keys for this ``documentType`` (BRD, SOP, etc.). */
  enrichmentFieldIds: string[];
};

export type DraftSessionListItem = {
  id: string;
  title: string;
  status: DraftSession["status"];
  ownerId: string;
  diagramType: DraftSession["diagramType"];
  documentType: DraftSession["documentType"];
  createdAt: string;
  updatedAt: string;
  draftGenerationStartedAt?: string | null;
  draftGenerationCompletedAt?: string | null;
  screenshotGenerationStartedAt?: string | null;
  screenshotGenerationCompletedAt?: string | null;
  draftGenerationDurationSeconds?: number | null;
  screenshotGenerationDurationSeconds?: number | null;
  latestStageTitle: string;
  latestStageDetail: string;
  failureDetail: string;
  resumeReady: boolean;
  canRetry: boolean;
  llmCallCount: number;
  totalPromptTokens: number;
  totalCompletionTokens: number;
  totalTokensReported: number;
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
