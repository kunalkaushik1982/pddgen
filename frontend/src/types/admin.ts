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

export type AdminMetricsColumnId =
  | "session"
  | "owner"
  | "status"
  | "llm_call_count"
  | "total_prompt_tokens"
  | "total_completion_tokens"
  | "total_tokens_reported"
  | "estimated_cost_usd"
  | "actual_ai_cost_inr"
  | "charge_inr_with_margin"
  | "processing_cost_inr"
  | "storage_bytes_total"
  | "storage_cost_inr"
  | "total_estimated_cost_inr"
  | "draft_generation_runs"
  | "draft_generation_seconds_total"
  | "screenshot_generation_runs"
  | "screenshot_generation_seconds_total"
  | "updated_at";

export type AdminPreferences = {
  sessionMetricsVisibleColumns: AdminMetricsColumnId[];
  metricsSelectedOwnerId?: string | null;
};

export type MetricOwnerOption = {
  id: string;
  label: string;
};

export const DEFAULT_ADMIN_METRIC_COLUMNS: AdminMetricsColumnId[] = [
  "session",
  "owner",
  "status",
  "total_estimated_cost_inr",
  "updated_at",
];

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
