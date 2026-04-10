/**
 * Purpose: Admin visibility over all users, jobs, and usage metrics.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\AdminPage.tsx
 */

import React, { useMemo, useState } from "react";

import type { AdminJobSummary, AdminMetricsColumnId, AdminSessionMetrics, AdminUserSummary } from "../types/admin";
import { formatGenerationTimeSummary } from "../utils/formatWallDuration";

type AdminPageProps = {
  users: AdminUserSummary[];
  jobs: AdminJobSummary[];
  sessionMetrics: AdminSessionMetrics[];
  visibleMetricColumns: AdminMetricsColumnId[];
  onVisibleMetricColumnsChange: (columns: AdminMetricsColumnId[]) => Promise<unknown>;
  isLoading?: boolean;
};

function formatSecondsTotal(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "0s";
  }
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const m = Math.floor(seconds / 60);
  const s = seconds - m * 60;
  return `${m}m ${s.toFixed(0)}s`;
}

function formatUsd(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "—";
  }
  return `$${value.toFixed(4)}`;
}

const inrFmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });

function formatInr(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "—";
  }
  return inrFmt.format(value);
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 ** 2) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  if (bytes < 1024 ** 3) {
    return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  }
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

type ColumnDefinition = {
  id: AdminMetricsColumnId;
  label: string;
  render: (row: AdminSessionMetrics) => React.ReactNode;
};

const metricColumnDefinitions: ColumnDefinition[] = [
  {
    id: "session",
    label: "Session",
    render: (row) => (
      <>
        <div className="admin-metrics-title">{row.title}</div>
        <div className="artifact-meta">{row.sessionId}</div>
      </>
    ),
  },
  { id: "owner", label: "Owner", render: (row) => row.ownerId },
  { id: "status", label: "Status", render: (row) => row.status },
  { id: "llm_call_count", label: "LLM calls", render: (row) => row.llmCallCount },
  { id: "total_prompt_tokens", label: "Prompt tok", render: (row) => row.totalPromptTokens },
  { id: "total_completion_tokens", label: "Completion tok", render: (row) => row.totalCompletionTokens },
  { id: "total_tokens_reported", label: "Σ total tok", render: (row) => row.totalTokensReported ?? "—" },
  { id: "estimated_cost_usd", label: "Est. USD", render: (row) => formatUsd(row.estimatedCostUsd) },
  { id: "actual_ai_cost_inr", label: "Actual AI (INR)", render: (row) => formatInr(row.actualAiCostInr) },
  { id: "charge_inr_with_margin", label: "Charge AI+margin (INR)", render: (row) => formatInr(row.chargeInrWithMargin) },
  { id: "processing_cost_inr", label: "Processing (INR)", render: (row) => formatInr(row.processingCostInr) },
  { id: "storage_bytes_total", label: "Storage used", render: (row) => formatBytes(row.storageBytesTotal) },
  { id: "storage_cost_inr", label: "Storage (INR)", render: (row) => formatInr(row.storageCostInr) },
  {
    id: "total_estimated_cost_inr",
    label: "Total est. (INR)",
    render: (row) => <strong>{formatInr(row.totalEstimatedCostInr)}</strong>,
  },
  { id: "draft_generation_runs", label: "Draft jobs", render: (row) => row.draftGenerationRuns },
  { id: "draft_generation_seconds_total", label: "Draft time", render: (row) => formatSecondsTotal(row.draftGenerationSecondsTotal) },
  { id: "screenshot_generation_runs", label: "Screenshot jobs", render: (row) => row.screenshotGenerationRuns },
  {
    id: "screenshot_generation_seconds_total",
    label: "Screenshot time",
    render: (row) => formatSecondsTotal(row.screenshotGenerationSecondsTotal),
  },
  { id: "updated_at", label: "Updated", render: (row) => new Date(row.updatedAt).toLocaleString() },
];

export function AdminPage({
  users,
  jobs,
  sessionMetrics,
  visibleMetricColumns,
  onVisibleMetricColumnsChange,
  isLoading = false,
}: AdminPageProps): React.JSX.Element {
  const totalAiCostInr = sessionMetrics.reduce((sum, row) => sum + (row.actualAiCostInr ?? 0), 0);
  const totalProcessingCostInr = sessionMetrics.reduce((sum, row) => sum + row.processingCostInr, 0);
  const totalStorageCostInr = sessionMetrics.reduce((sum, row) => sum + row.storageCostInr, 0);
  const totalEstimatedCostInr = sessionMetrics.reduce((sum, row) => sum + row.totalEstimatedCostInr, 0);
  const totalStorageBytes = sessionMetrics.reduce((sum, row) => sum + row.storageBytesTotal, 0);
  const [columnPickerOpen, setColumnPickerOpen] = useState(false);
  const visibleColumnDefinitions = useMemo(
    () => metricColumnDefinitions.filter((column) => visibleMetricColumns.includes(column.id)),
    [visibleMetricColumns],
  );

  const toggleColumn = async (columnId: AdminMetricsColumnId) => {
    const nextColumns = visibleMetricColumns.includes(columnId)
      ? visibleMetricColumns.filter((id) => id !== columnId)
      : [...visibleMetricColumns, columnId];
    await onVisibleMetricColumnsChange(nextColumns);
  };

  return (
    <div className="stack">
      <section className="panel stack">
        <div className="section-header-inline">
          <div>
            <h2>Admin Overview</h2>
            <p className="muted">Read-only visibility across all registered users and all draft jobs.</p>
          </div>
        </div>
        <div className="button-row">
          <div className="panel">
            <strong>{users.length}</strong>
            <div className="artifact-meta">Users</div>
          </div>
          <div className="panel">
            <strong>{jobs.length}</strong>
            <div className="artifact-meta">Jobs</div>
          </div>
          <div className="panel">
            <strong>{jobs.filter((job) => job.status === "processing").length}</strong>
            <div className="artifact-meta">Running</div>
          </div>
        </div>
      </section>

      <section className="panel stack">
        <div className="section-header-inline">
          <div>
            <h2>Usage metrics (per session)</h2>
            <p className="muted">
              Includes AI, processing-time, and storage estimates. Configure rates in backend env settings for operational
              cost tracking.
            </p>
          </div>
          <div className="admin-column-picker">
            <button
              type="button"
              className="button-secondary"
              onClick={() => setColumnPickerOpen((open) => !open)}
              aria-expanded={columnPickerOpen}
            >
              Columns
            </button>
            {columnPickerOpen ? (
              <div className="admin-column-picker-menu">
                {metricColumnDefinitions.map((column) => (
                  <label key={column.id} className="admin-column-picker-option">
                    <input
                      type="checkbox"
                      checked={visibleMetricColumns.includes(column.id)}
                      onChange={() => void toggleColumn(column.id)}
                    />
                    <span>{column.label}</span>
                  </label>
                ))}
              </div>
            ) : null}
          </div>
        </div>
        <div className="admin-cost-summary-grid">
          <div className="admin-cost-summary-card">
            <div className="artifact-meta">AI cost (INR)</div>
            <strong>{formatInr(totalAiCostInr)}</strong>
          </div>
          <div className="admin-cost-summary-card">
            <div className="artifact-meta">Processing cost (INR)</div>
            <strong>{formatInr(totalProcessingCostInr)}</strong>
          </div>
          <div className="admin-cost-summary-card">
            <div className="artifact-meta">Storage cost (INR)</div>
            <strong>{formatInr(totalStorageCostInr)}</strong>
          </div>
          <div className="admin-cost-summary-card">
            <div className="artifact-meta">Estimated total (INR)</div>
            <strong>{formatInr(totalEstimatedCostInr)}</strong>
          </div>
          <div className="admin-cost-summary-card">
            <div className="artifact-meta">Tracked storage</div>
            <strong>{formatBytes(totalStorageBytes)}</strong>
          </div>
        </div>
        {sessionMetrics.length > 0 ? (
          <div className="admin-metrics-scroll">
            <table className="admin-metrics-table">
              <thead>
                <tr>
                  {visibleColumnDefinitions.map((column) => (
                    <th key={column.id}>{column.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sessionMetrics.map((row) => (
                  <tr key={row.sessionId}>
                    {visibleColumnDefinitions.map((column) => (
                      <td key={column.id}>{column.render(row)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">{isLoading ? "Loading metrics..." : "No session metrics recorded yet."}</div>
        )}
      </section>

      <section className="panel stack">
        <div className="section-header-inline">
          <div>
            <h2>Users</h2>
            <p className="muted">All application users with admin membership and job counts.</p>
          </div>
        </div>
        {users.length > 0 ? (
          <div className="history-list">
            {users.map((user) => (
              <div key={user.id} className="history-card">
                <div className="history-card-main">
                  <strong>{user.username}</strong>
                  <div className="artifact-meta">Created {new Date(user.createdAt).toLocaleString()}</div>
                  <div className="artifact-meta">Role: {user.isAdmin ? "Admin" : "User"}</div>
                  <div className="artifact-meta">Total jobs: {user.totalJobs}</div>
                  <div className="artifact-meta">Active jobs: {user.activeJobs}</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">{isLoading ? "Loading users..." : "No users found."}</div>
        )}
      </section>

      <section className="panel stack">
        <div className="section-header-inline">
          <div>
            <h2>All Jobs</h2>
            <p className="muted">Cross-user job visibility for support and operational monitoring.</p>
          </div>
        </div>
        {jobs.length > 0 ? (
          <div className="history-list">
            {jobs.map((job) => {
              const generationSummary = formatGenerationTimeSummary(job);
              return (
                <div key={job.id} className="history-card">
                  <div className="history-card-main">
                    <strong>{job.title}</strong>
                    <div className="artifact-meta">Owner: {job.ownerId}</div>
                    <div className="artifact-meta">
                      {job.status} | updated {new Date(job.updatedAt).toLocaleString()}
                    </div>
                    <div className="artifact-meta">Session ID: {job.id}</div>
                    <div className="artifact-meta">{job.latestStageTitle}</div>
                    <div className="artifact-meta">{job.failureDetail || job.latestStageDetail}</div>
                    {generationSummary ? (
                      <div className="artifact-meta muted">Last run times: {generationSummary}</div>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="empty-state">{isLoading ? "Loading jobs..." : "No jobs found."}</div>
        )}
      </section>
    </div>
  );
}
