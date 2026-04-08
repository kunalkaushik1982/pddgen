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
};
