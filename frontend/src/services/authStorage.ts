const AUTH_TOKEN_KEY = "pdd_generator_auth_token";

export const authStorage = {
  getToken(): string {
    if (typeof window === "undefined") {
      return "";
    }
    return window.sessionStorage.getItem(AUTH_TOKEN_KEY) ?? "";
  },

  setToken(token: string): void {
    if (typeof window === "undefined") {
      return;
    }
    window.sessionStorage.setItem(AUTH_TOKEN_KEY, token);
  },

  clearToken(): void {
    if (typeof window === "undefined") {
      return;
    }
    window.sessionStorage.removeItem(AUTH_TOKEN_KEY);
  },
};
