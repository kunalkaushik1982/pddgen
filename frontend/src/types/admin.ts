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
