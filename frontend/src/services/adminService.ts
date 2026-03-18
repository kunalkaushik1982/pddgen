import type { AdminJobSummary, AdminUserSummary } from "../types/admin";
import type { BackendAdminUserSummary, BackendDraftSessionListItem } from "./contracts";
import { fetchJson } from "./http";
import { mapAdminUserSummary, mapDraftSessionListItem } from "./mappers";

export const adminService = {
  async listUsers(): Promise<AdminUserSummary[]> {
    const users = await fetchJson<BackendAdminUserSummary[]>("/admin/users");
    return users.map(mapAdminUserSummary);
  },

  async listJobs(): Promise<AdminJobSummary[]> {
    const jobs = await fetchJson<BackendDraftSessionListItem[]>("/admin/jobs");
    return jobs.map(mapDraftSessionListItem);
  },
};
