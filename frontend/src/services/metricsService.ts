import type {
  AdminJobSummary,
  AdminPreferences,
  AdminSessionMetrics,
  AdminUserSummary,
  MetricOwnerOption,
} from "../types/admin";
import type {
  BackendAdminPreferences,
  BackendAdminSessionMetrics,
  BackendAdminUserSummary,
  BackendDraftSessionListItem,
  BackendMetricsOwnerOption,
} from "./contracts";
import { fetchJson } from "./http";
import { mapAdminSessionMetrics, mapAdminUserSummary, mapDraftSessionListItem } from "./mappers";

function buildOwnerQuery(ownerId?: string | null): string {
  if (!ownerId || ownerId === "all") {
    return "";
  }
  return `?owner_id=${encodeURIComponent(ownerId)}`;
}

export const metricsService = {
  async listUsers(): Promise<AdminUserSummary[]> {
    const rows = await fetchJson<BackendAdminUserSummary[]>("/admin/users");
    return rows.map(mapAdminUserSummary);
  },

  async updateUserQuota(
    userId: string,
    payload: { quotaLifetimeBonus: number; quotaDailyBonus: number },
  ): Promise<AdminUserSummary> {
    const row = await fetchJson<BackendAdminUserSummary>(`/admin/users/${encodeURIComponent(userId)}/quota`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        quota_lifetime_bonus: payload.quotaLifetimeBonus,
        quota_daily_bonus: payload.quotaDailyBonus,
      }),
    });
    return mapAdminUserSummary(row);
  },

  async listOwners(): Promise<MetricOwnerOption[]> {
    const payload = await fetchJson<BackendMetricsOwnerOption[]>("/metrics/owners");
    return payload.map((item) => ({ id: item.id, label: item.label }));
  },

  async listJobs(ownerId?: string | null): Promise<AdminJobSummary[]> {
    const jobs = await fetchJson<BackendDraftSessionListItem[]>(`/metrics/jobs${buildOwnerQuery(ownerId)}`);
    return jobs.map(mapDraftSessionListItem);
  },

  async listSessionMetrics(ownerId?: string | null): Promise<AdminSessionMetrics[]> {
    const rows = await fetchJson<BackendAdminSessionMetrics[]>(`/metrics/sessions${buildOwnerQuery(ownerId)}`);
    return rows.map(mapAdminSessionMetrics);
  },

  async getPreferences(): Promise<AdminPreferences> {
    const payload = await fetchJson<BackendAdminPreferences>("/metrics/preferences");
    return {
      sessionMetricsVisibleColumns: payload.session_metrics_visible_columns as AdminPreferences["sessionMetricsVisibleColumns"],
      metricsSelectedOwnerId: payload.metrics_selected_owner_id ?? null,
    };
  },

  async updatePreferences(preferences: AdminPreferences): Promise<AdminPreferences> {
    const payload = await fetchJson<BackendAdminPreferences>("/metrics/preferences", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_metrics_visible_columns: preferences.sessionMetricsVisibleColumns,
        metrics_selected_owner_id: preferences.metricsSelectedOwnerId ?? null,
      }),
    });
    return {
      sessionMetricsVisibleColumns: payload.session_metrics_visible_columns as AdminPreferences["sessionMetricsVisibleColumns"],
      metricsSelectedOwnerId: payload.metrics_selected_owner_id ?? null,
    };
  },
};
