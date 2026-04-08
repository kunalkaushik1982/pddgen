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

  async loginWithGoogle(idToken: string): Promise<User> {
    const payload = await fetchJson<BackendAuthResponse>("/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_token: idToken }),
    });
    if (!payload.user) {
      throw new Error(payload.challenge_type ?? "Google authentication failed.");
    }
    return mapUser(payload.user);
  },

  async requestPasswordReset(username: string): Promise<{ accepted: boolean; reset_token?: string | null }> {
    return fetchJson<{ accepted: boolean; reset_token?: string | null }>("/auth/password-reset/request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username }),
    });
  },

  async confirmPasswordReset(token: string, newPassword: string): Promise<void> {
    await fetchJson<void>("/auth/password-reset/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: newPassword }),
    });
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
