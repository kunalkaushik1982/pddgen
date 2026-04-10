import type { AdminJobSummary, AdminSessionMetrics, AdminUserSummary } from "../types/admin";
import type { BackendAdminSessionMetrics, BackendAdminUserSummary, BackendDraftSessionListItem } from "./contracts";
import { fetchJson } from "./http";
import { mapAdminSessionMetrics, mapAdminUserSummary, mapDraftSessionListItem } from "./mappers";

export const adminService = {
  async listUsers(): Promise<AdminUserSummary[]> {
    const users = await fetchJson<BackendAdminUserSummary[]>("/admin/users");
    return users.map(mapAdminUserSummary);
  },

  async listJobs(): Promise<AdminJobSummary[]> {
    const jobs = await fetchJson<BackendDraftSessionListItem[]>("/admin/jobs");
    return jobs.map(mapDraftSessionListItem);
  },

  async listSessionMetrics(): Promise<AdminSessionMetrics[]> {
    const rows = await fetchJson<BackendAdminSessionMetrics[]>("/admin/metrics/sessions");
    return rows.map(mapAdminSessionMetrics);
  },
};
