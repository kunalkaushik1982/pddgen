import type { AdminJobSummary, AdminPreferences, AdminSessionMetrics, AdminUserSummary } from "../types/admin";
import type { BackendAdminPreferences, BackendAdminSessionMetrics, BackendAdminUserSummary, BackendDraftSessionListItem } from "./contracts";
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

  async getPreferences(): Promise<AdminPreferences> {
    const payload = await fetchJson<BackendAdminPreferences>("/admin/preferences");
    return {
      sessionMetricsVisibleColumns: payload.session_metrics_visible_columns as AdminPreferences["sessionMetricsVisibleColumns"],
    };
  },

  async updatePreferences(sessionMetricsVisibleColumns: AdminPreferences["sessionMetricsVisibleColumns"]): Promise<AdminPreferences> {
    const payload = await fetchJson<BackendAdminPreferences>("/admin/preferences", {
      method: "PUT",
      body: JSON.stringify({ session_metrics_visible_columns: sessionMetricsVisibleColumns }),
    });
    return {
      sessionMetricsVisibleColumns: payload.session_metrics_visible_columns as AdminPreferences["sessionMetricsVisibleColumns"],
    };
  },
};
