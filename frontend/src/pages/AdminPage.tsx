/**
 * Purpose: Admin visibility over all users, jobs, and usage metrics.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\AdminPage.tsx
 */

import React from "react";

import type { AdminJobSummary, AdminSessionMetrics, AdminUserSummary } from "../types/admin";
import { formatGenerationTimeSummary } from "../utils/formatWallDuration";

type AdminPageProps = {
  users: AdminUserSummary[];
  jobs: AdminJobSummary[];
  sessionMetrics: AdminSessionMetrics[];
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

export function AdminPage({ users, jobs, sessionMetrics, isLoading = false }: AdminPageProps): React.JSX.Element {
  const totalAiCostInr = sessionMetrics.reduce((sum, row) => sum + (row.actualAiCostInr ?? 0), 0);
  const totalProcessingCostInr = sessionMetrics.reduce((sum, row) => sum + row.processingCostInr, 0);
  const totalStorageCostInr = sessionMetrics.reduce((sum, row) => sum + row.storageCostInr, 0);
  const totalEstimatedCostInr = sessionMetrics.reduce((sum, row) => sum + row.totalEstimatedCostInr, 0);
  const totalStorageBytes = sessionMetrics.reduce((sum, row) => sum + row.storageBytesTotal, 0);

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
                  <th>Session</th>
                  <th>Owner</th>
                  <th>Status</th>
                  <th>LLM calls</th>
                  <th>Prompt tok</th>
                  <th>Completion tok</th>
                  <th>Σ total tok</th>
                  <th>Est. USD</th>
                  <th>Actual AI (INR)</th>
                  <th>Charge AI+margin (INR)</th>
                  <th>Processing (INR)</th>
                  <th>Storage used</th>
                  <th>Storage (INR)</th>
                  <th>Total est. (INR)</th>
                  <th>Draft jobs</th>
                  <th>Draft time</th>
                  <th>Screenshot jobs</th>
                  <th>Screenshot time</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {sessionMetrics.map((m) => (
                  <tr key={m.sessionId}>
                    <td>
                      <div className="admin-metrics-title">{m.title}</div>
                      <div className="artifact-meta">{m.sessionId}</div>
                    </td>
                    <td>{m.ownerId}</td>
                    <td>{m.status}</td>
                    <td>{m.llmCallCount}</td>
                    <td>{m.totalPromptTokens}</td>
                    <td>{m.totalCompletionTokens}</td>
                    <td>{m.totalTokensReported ?? "—"}</td>
                    <td>{formatUsd(m.estimatedCostUsd)}</td>
                    <td>{formatInr(m.actualAiCostInr)}</td>
                    <td>{formatInr(m.chargeInrWithMargin)}</td>
                    <td>{formatInr(m.processingCostInr)}</td>
                    <td>{formatBytes(m.storageBytesTotal)}</td>
                    <td>{formatInr(m.storageCostInr)}</td>
                    <td>
                      <strong>{formatInr(m.totalEstimatedCostInr)}</strong>
                    </td>
                    <td>{m.draftGenerationRuns}</td>
                    <td>{formatSecondsTotal(m.draftGenerationSecondsTotal)}</td>
                    <td>{m.screenshotGenerationRuns}</td>
                    <td>{formatSecondsTotal(m.screenshotGenerationSecondsTotal)}</td>
                    <td>{new Date(m.updatedAt).toLocaleString()}</td>
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
