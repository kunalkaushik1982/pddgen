import type { User } from "../types/auth";
import type { BackendAuthResponse, BackendUser } from "./contracts";
import { fetchJson, HttpError } from "./http";
import { mapUser } from "./mappers";

export const authService = {
  async register(username: string, password: string, email: string): Promise<User> {
    const payload = await fetchJson<BackendAuthResponse>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, email }),
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

  async loginWithGoogle(accessToken: string): Promise<User> {
    const payload = await fetchJson<BackendAuthResponse>("/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_token: accessToken }),
    });
    if (!payload.user) {
      throw new Error(payload.challenge_type ?? "Google authentication failed.");
    }
    return mapUser(payload.user);
  },

  async requestPasswordReset(email: string): Promise<{ accepted: boolean; reset_token?: string | null }> {
    return fetchJson<{ accepted: boolean; reset_token?: string | null }>("/auth/password-reset/request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
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

  async getCurrentUser(): Promise<User | null> {
    try {
      const user = await fetchJson<BackendUser | null>("/auth/me");
      if (!user) {
        return null;
      }
      return mapUser(user);
    } catch (error) {
      if (error instanceof HttpError && error.status === 401) {
        return null;
      }
      throw error;
    }
  },

  clearAuthToken(): void {
    return;
  },
};
