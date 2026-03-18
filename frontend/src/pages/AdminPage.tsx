/**
 * Purpose: Admin visibility over all users and all jobs.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\AdminPage.tsx
 */

import React from "react";

import type { AdminJobSummary, AdminUserSummary } from "../types/admin";

type AdminPageProps = {
  users: AdminUserSummary[];
  jobs: AdminJobSummary[];
  isLoading?: boolean;
};

export function AdminPage({ users, jobs, isLoading = false }: AdminPageProps): React.JSX.Element {
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
            {jobs.map((job) => (
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
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">{isLoading ? "Loading jobs..." : "No jobs found."}</div>
        )}
      </section>
    </div>
  );
}
