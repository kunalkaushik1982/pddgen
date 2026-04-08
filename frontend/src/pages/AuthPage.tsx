/**
 * Purpose: Simple username/password login and registration page.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\AuthPage.tsx
 */

import React, { useEffect, useRef, useState } from "react";
import { uiCopy } from "../constants/uiCopy";

type AuthPageProps = {
  disabled?: boolean;
  message?: { tone: "info" | "error"; text: string } | null;
  onLogin: (username: string, password: string) => Promise<void>;
  onRegister: (username: string, password: string) => Promise<void>;
  onGoogleLogin: (accessToken: string) => Promise<void>;
  onRequestPasswordReset: (username: string) => Promise<void>;
  onConfirmPasswordReset: (token: string, newPassword: string) => Promise<void>;
};

declare global {
  interface Window {
    google?: {
      accounts: {
        oauth2: {
          initTokenClient: (cfg: {
            client_id: string;
            scope: string;
            callback: (res: { access_token?: string; error?: string }) => void;
            prompt?: "consent" | "select_account" | "";
          }) => { requestAccessToken: (opts?: { prompt?: "consent" | "select_account" | "" }) => void };
        };
      };
    };
  }
}

const GOOGLE_SCRIPT_ID = "google-identity-services";

function loadGoogleScript(): Promise<void> {
  if (window.google?.accounts?.oauth2) {
    return Promise.resolve();
  }
  const existing = document.getElementById(GOOGLE_SCRIPT_ID) as HTMLScriptElement | null;
  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Failed to load Google script.")));
    });
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.id = GOOGLE_SCRIPT_ID;
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google script."));
    document.head.appendChild(script);
  });
}

export function AuthPage({
  disabled,
  message,
  onLogin,
  onRegister,
  onGoogleLogin,
  onRequestPasswordReset,
  onConfirmPasswordReset,
}: AuthPageProps): React.JSX.Element {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const googleClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined)?.trim() ?? "";
  const googleTokenClientRef = useRef<{
    requestAccessToken: (opts?: { prompt?: "consent" | "select_account" | "" }) => void;
  } | null>(null);
  const googleRequestInFlightRef = useRef(false);
  const [googleReady, setGoogleReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!googleClientId) {
      setGoogleReady(false);
      googleTokenClientRef.current = null;
      return () => {};
    }
    void loadGoogleScript()
      .then(() => {
        if (cancelled || !window.google?.accounts?.oauth2 || googleTokenClientRef.current) {
          if (!cancelled && window.google?.accounts?.oauth2) {
            setGoogleReady(true);
          }
          return;
        }
        const tokenClient = window.google.accounts.oauth2.initTokenClient({
          client_id: googleClientId,
          scope: "openid email profile",
          prompt: "select_account",
          callback: (result) => {
            googleRequestInFlightRef.current = false;
            const accessToken = result.access_token;
            if (!accessToken || result.error) {
              return;
            }
            void onGoogleLogin(accessToken);
          },
        });
        googleTokenClientRef.current = tokenClient;
        setGoogleReady(true);
      })
      .catch(() => {
        if (!cancelled) {
          setGoogleReady(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [googleClientId, onGoogleLogin]);

  const startGoogleLogin = async () => {
    if (!googleClientId || !googleReady) {
      return;
    }
    if (!window.google?.accounts?.oauth2 || !googleTokenClientRef.current) {
      throw new Error("Google Sign-In is unavailable.");
    }
    if (googleRequestInFlightRef.current) {
      return;
    }
    googleRequestInFlightRef.current = true;
    googleTokenClientRef.current.requestAccessToken({ prompt: "select_account" });
    window.setTimeout(() => {
      googleRequestInFlightRef.current = false;
    }, 5000);
  };

  return (
    <main className="auth-shell">
      <section className="panel stack auth-panel">
        <div>
          <h1 className="app-title">{uiCopy.appTitle}</h1>
          <p className="app-subtitle">Sign in to create new sessions and reopen previous work.</p>
        </div>

        {message ? <div className={`status-banner ${message.tone === "error" ? "error" : ""}`}>{message.text}</div> : null}

        <label className="field-group">
          <span>Username</span>
          <input value={username} onChange={(event) => setUsername(event.target.value)} placeholder="analyst1" />
        </label>

        <label className="field-group">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter password"
          />
        </label>

        <div className="button-row">
          <button type="button" className="button-primary" disabled={disabled} onClick={() => void onLogin(username, password)}>
            Sign in
          </button>
          <button type="button" className="button-secondary" disabled={disabled} onClick={() => void onRegister(username, password)}>
            Create account
          </button>
        </div>
        {googleClientId ? (
          <button type="button" className="button-secondary" disabled={disabled || !googleReady} onClick={() => void startGoogleLogin()}>
            Continue with Google
          </button>
        ) : null}

        <hr />
        <div className="stack">
          <h3 className="panel-title">Forgot password?</h3>
          <p className="muted">Request a reset token, then confirm reset with the token and your new password.</p>
          <button type="button" className="button-secondary" disabled={disabled} onClick={() => void onRequestPasswordReset(username)}>
            Request password reset
          </button>
          <label className="field-group">
            <span>Reset token</span>
            <input value={resetToken} onChange={(event) => setResetToken(event.target.value)} placeholder="Paste reset token" />
          </label>
          <label className="field-group">
            <span>New password</span>
            <input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="Enter new password"
            />
          </label>
          <button
            type="button"
            className="button-secondary"
            disabled={disabled}
            onClick={() => void onConfirmPasswordReset(resetToken, newPassword)}
          >
            Confirm password reset
          </button>
        </div>
      </section>
    </main>
  );
}
