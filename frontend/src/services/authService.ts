import type { User } from "../types/auth";
import type { BackendAuthResponse, BackendUser } from "./contracts";
import { authStorage } from "./authStorage";
import { fetchJson } from "./http";
import { mapUser } from "./mappers";

export const authService = {
  async register(username: string, password: string): Promise<User> {
    const payload = await fetchJson<BackendAuthResponse>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    authStorage.setToken(payload.token);
    return mapUser(payload.user);
  },

  async login(username: string, password: string): Promise<User> {
    const payload = await fetchJson<BackendAuthResponse>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    authStorage.setToken(payload.token);
    return mapUser(payload.user);
  },

  async logout(): Promise<void> {
    const token = authStorage.getToken();
    if (!token) {
      return;
    }
    try {
      await fetchJson<void>("/auth/logout", {
        method: "POST",
      });
    } finally {
      authStorage.clearToken();
    }
  },

  async getCurrentUser(): Promise<User> {
    const user = await fetchJson<BackendUser>("/auth/me");
    return mapUser(user);
  },

  clearAuthToken(): void {
    authStorage.clearToken();
  },
};
