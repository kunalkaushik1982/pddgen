import type { AdminJobSummary, AdminPreferences, AdminSessionMetrics, MetricOwnerOption } from "../types/admin";
import type {
  BackendAdminPreferences,
  BackendAdminSessionMetrics,
  BackendDraftSessionListItem,
  BackendMetricsOwnerOption,
} from "./contracts";
import { fetchJson } from "./http";
import { mapAdminSessionMetrics, mapDraftSessionListItem } from "./mappers";

function buildOwnerQuery(ownerId?: string | null): string {
  if (!ownerId || ownerId === "all") {
    return "";
  }
  return `?owner_id=${encodeURIComponent(ownerId)}`;
}

export const metricsService = {
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
