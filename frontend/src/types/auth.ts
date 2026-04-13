/**
 * Purpose: Frontend auth and identity types.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\types\auth.ts
 */

export type User = {
  id: string;
  username: string;
  email?: string | null;
  emailVerified?: boolean;
  createdAt: string;
  isAdmin: boolean;
  /** When true, the app shows only the admin console (no workspace/projects/session). */
  adminConsoleOnly?: boolean;
  billingGstin?: string | null;
  billingLegalName?: string | null;
  billingStateCode?: string | null;
  quotaLifetimeBonus?: number;
  quotaDailyBonus?: number;
  jobUsageLifetime?: number;
  jobUsageDaily?: number;
  effectiveLifetimeCap?: number;
  effectiveDailyCap?: number;
};
