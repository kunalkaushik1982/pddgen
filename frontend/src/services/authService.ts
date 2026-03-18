import type { User } from "../types/auth";
import type { BackendAuthResponse, BackendUser } from "./contracts";
import { fetchJson } from "./http";
import { mapUser } from "./mappers";

export const authService = {
  async register(username: string, password: string): Promise<User> {
    const payload = await fetchJson<BackendAuthResponse>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!payload.user) {
      throw new Error(payload.challenge_type ?? "Additional authentication challenge required.");
    }
    return mapUser(payload.user);
  },

  async login(username: string, password: string): Promise<User> {
    const payload = await fetchJson<BackendAuthResponse>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!payload.user) {
      throw new Error(payload.challenge_type ?? "Additional authentication challenge required.");
    }
    return mapUser(payload.user);
  },

  async logout(): Promise<void> {
    await fetchJson<void>("/auth/logout", {
      method: "POST",
    });
  },

  async getCurrentUser(): Promise<User> {
    const user = await fetchJson<BackendUser>("/auth/me");
    return mapUser(user);
  },

  clearAuthToken(): void {
    return;
  },
};
