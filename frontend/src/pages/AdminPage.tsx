/**
 * Purpose: Admin visibility over all users, jobs, and usage metrics.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\AdminPage.tsx
 */

import React, { useEffect, useMemo, useState } from "react";

import type {
  AdminJobSummary,
  AdminMetricsColumnId,
  AdminSessionMetrics,
  AdminUserSummary,
  MetricOwnerOption,
} from "../types/admin";
import { formatGenerationTimeSummary } from "../utils/formatWallDuration";

type AdminPageProps = {
  users: AdminUserSummary[];
  jobs: AdminJobSummary[];
  sessionMetrics: AdminSessionMetrics[];
  visibleMetricColumns: AdminMetricsColumnId[];
  onVisibleMetricColumnsChange: (columns: AdminMetricsColumnId[]) => Promise<unknown>;
  ownerOptions?: MetricOwnerOption[];
  selectedOwnerId?: string | null;
  onSelectedOwnerIdChange?: (ownerId: string) => Promise<unknown>;
  isAdminView?: boolean;
  isLoading?: boolean;
  onUpdateUserQuota?: (userId: string, payload: { quotaLifetimeBonus: number; quotaDailyBonus: number }) => Promise<unknown>;
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

type AdminTabId = "overview" | "quotas" | "usage" | "jobs";

export function AdminPage({
  users,
  jobs,
  sessionMetrics,
  visibleMetricColumns,
  onVisibleMetricColumnsChange,
  ownerOptions = [],
  selectedOwnerId = null,
  onSelectedOwnerIdChange,
  isAdminView = false,
  isLoading = false,
  onUpdateUserQuota,
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

  const [quotaDrafts, setQuotaDrafts] = useState<Record<string, { lifetime: number; daily: number }>>({});
  const showQuotasTab = Boolean(isAdminView && onUpdateUserQuota);
  const [activeTab, setActiveTab] = useState<AdminTabId>("overview");

  useEffect(() => {
    const next: Record<string, { lifetime: number; daily: number }> = {};
    for (const u of users) {
      next[u.id] = { lifetime: u.quotaLifetimeBonus, daily: u.quotaDailyBonus };
    }
    setQuotaDrafts(next);
  }, [users]);

  useEffect(() => {
    if (!showQuotasTab && activeTab === "quotas") {
      setActiveTab("overview");
    }
  }, [showQuotasTab, activeTab]);

  const toggleColumn = async (columnId: AdminMetricsColumnId) => {
    const nextColumns = visibleMetricColumns.includes(columnId)
      ? visibleMetricColumns.filter((id) => id !== columnId)
      : [...visibleMetricColumns, columnId];
    await onVisibleMetricColumnsChange(nextColumns);
  };

  return (
    <div className="stack">
      <div className="panel stack">
        <div className="admin-page-tabs" role="tablist" aria-label="Admin sections">
          <button
            type="button"
            id="admin-tab-overview"
            role="tab"
            aria-selected={activeTab === "overview"}
            aria-controls="admin-panel-overview"
            className={`admin-page-tab ${activeTab === "overview" ? "admin-page-tab-active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            Overview
          </button>
          {showQuotasTab ? (
            <button
              type="button"
              id="admin-tab-quotas"
              role="tab"
              aria-selected={activeTab === "quotas"}
              aria-controls="admin-panel-quotas"
              className={`admin-page-tab ${activeTab === "quotas" ? "admin-page-tab-active" : ""}`}
              onClick={() => setActiveTab("quotas")}
            >
              Quotas
            </button>
          ) : null}
          <button
            type="button"
            id="admin-tab-usage"
            role="tab"
            aria-selected={activeTab === "usage"}
            aria-controls="admin-panel-usage"
            className={`admin-page-tab ${activeTab === "usage" ? "admin-page-tab-active" : ""}`}
            onClick={() => setActiveTab("usage")}
          >
            Usage
          </button>
          <button
            type="button"
            id="admin-tab-jobs"
            role="tab"
            aria-selected={activeTab === "jobs"}
            aria-controls="admin-panel-jobs"
            className={`admin-page-tab ${activeTab === "jobs" ? "admin-page-tab-active" : ""}`}
            onClick={() => setActiveTab("jobs")}
          >
            Jobs
          </button>
        </div>
      </div>

      {activeTab === "overview" ? (
        <section className="panel stack admin-tab-panel" id="admin-panel-overview" role="tabpanel" aria-labelledby="admin-tab-overview">
          <div className="section-header-inline">
            <div>
              <h2>Metrics Overview</h2>
              <p className="muted">
                {isAdminView
                  ? "Cross-user operational visibility with owner scoping."
                  : "Your job activity, AI usage, processing time, and storage metrics."}
              </p>
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
      ) : null}

      {activeTab === "quotas" && showQuotasTab && onUpdateUserQuota ? (
        <section className="panel stack admin-tab-panel" id="admin-panel-quotas" role="tabpanel" aria-labelledby="admin-tab-quotas">
          <div className="section-header-inline">
            <div>
              <h2>User job quotas</h2>
              <p className="muted">
                Each new session and each generate / screenshot run counts as one job unit. Global defaults come from
                backend env; bonuses add on top. Admin accounts are unlimited.
              </p>
            </div>
          </div>
          {users.length > 0 ? (
            <div className="admin-metrics-scroll">
              <table className="admin-metrics-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Lifetime used / cap</th>
                    <th>Daily used / cap</th>
                    <th>Bonus lifetime</th>
                    <th>Bonus daily</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const draft = quotaDrafts[u.id] ?? { lifetime: u.quotaLifetimeBonus, daily: u.quotaDailyBonus };
                    return (
                      <tr key={u.id}>
                        <td>
                          <strong>{u.username}</strong>
                          {u.isAdmin ? <div className="artifact-meta">Admin (unlimited)</div> : null}
                        </td>
                        <td>
                          {u.jobUsageLifetime} / {u.effectiveLifetimeCap}
                        </td>
                        <td>
                          {u.jobUsageDaily} / {u.effectiveDailyCap}
                        </td>
                        <td>
                          <input
                            type="number"
                            min={0}
                            className="input-compact"
                            disabled={u.isAdmin}
                            value={draft.lifetime}
                            onChange={(event) =>
                              setQuotaDrafts((prev) => ({
                                ...prev,
                                [u.id]: { ...draft, lifetime: Number.parseInt(event.target.value, 10) || 0 },
                              }))
                            }
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            min={0}
                            className="input-compact"
                            disabled={u.isAdmin}
                            value={draft.daily}
                            onChange={(event) =>
                              setQuotaDrafts((prev) => ({
                                ...prev,
                                [u.id]: { ...draft, daily: Number.parseInt(event.target.value, 10) || 0 },
                              }))
                            }
                          />
                        </td>
                        <td>
                          <button
                            type="button"
                            className="button-secondary"
                            disabled={u.isAdmin}
                            onClick={() =>
                              void onUpdateUserQuota(u.id, {
                                quotaLifetimeBonus: draft.lifetime,
                                quotaDailyBonus: draft.daily,
                              })
                            }
                          >
                            Save
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">{isLoading ? "Loading users..." : "No users loaded."}</div>
          )}
        </section>
      ) : null}

      {activeTab === "usage" ? (
        <section className="panel stack admin-tab-panel" id="admin-panel-usage" role="tabpanel" aria-labelledby="admin-tab-usage">
          <div className="section-header-inline">
            <div>
              <h2>Usage metrics (per session)</h2>
              <p className="muted">
                Includes AI, processing-time, and storage estimates. Configure rates in backend env settings for operational
                cost tracking.
              </p>
            </div>
            <div className="admin-filter-bar">
              {isAdminView && onSelectedOwnerIdChange ? (
                <label className="admin-filter-field">
                  <span>Owner</span>
                  <select value={selectedOwnerId ?? "all"} onChange={(event) => void onSelectedOwnerIdChange(event.target.value)}>
                    <option value="all">All users</option>
                    {ownerOptions.map((owner) => (
                      <option key={owner.id} value={owner.id}>
                        {owner.label}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
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
      ) : null}

      {activeTab === "jobs" ? (
        <section className="panel stack admin-tab-panel" id="admin-panel-jobs" role="tabpanel" aria-labelledby="admin-tab-jobs">
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
      ) : null}
    </div>
  );
}
