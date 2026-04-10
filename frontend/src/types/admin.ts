/**
 * Purpose: Frontend types for admin-visible user and job data.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\types\admin.ts
 */

import type { DraftSessionListItem } from "./session";

export type AdminUserSummary = {
  id: string;
  username: string;
  createdAt: string;
  isAdmin: boolean;
  totalJobs: number;
  activeJobs: number;
};

export type AdminJobSummary = DraftSessionListItem;

export type AdminSessionMetrics = {
  sessionId: string;
  title: string;
  ownerId: string;
  status: string;
  updatedAt: string;
  llmCallCount: number;
  totalPromptTokens: number;
  totalCompletionTokens: number;
  totalTokensReported: number | null;
  estimatedCostUsd: number | null;
  actualAiCostInr: number | null;
  chargeInrWithMargin: number | null;
  processingCostInr: number;
  storageBytesTotal: number;
  storageCostInr: number;
  totalEstimatedCostInr: number;
  draftGenerationSecondsTotal: number;
  draftGenerationRuns: number;
  screenshotGenerationSecondsTotal: number;
  screenshotGenerationRuns: number;
};
