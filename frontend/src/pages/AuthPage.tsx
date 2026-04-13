/**
 * Purpose: Simple username/password login and registration page.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\AuthPage.tsx
 */

import React, { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AuthLegalFooter } from "../components/legal/AuthLegalFooter";
import { uiCopy } from "../constants/uiCopy";
import { useToast } from "../providers/ToastProvider";

type AuthPageProps = {
  disabled?: boolean;
  message?: { tone: "info" | "error"; text: string } | null;
  onLogin: (username: string, password: string) => Promise<void>;
  onGoogleLogin: (accessToken: string) => Promise<void>;
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
  onGoogleLogin,
}: AuthPageProps): React.JSX.Element {
  const [searchParams] = useSearchParams();
  const { showToast } = useToast();
  const emailVerifiedToastShown = useRef(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const googleClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined)?.trim() ?? "";
  const googleTokenClientRef = useRef<{
    requestAccessToken: (opts?: { prompt?: "consent" | "select_account" | "" }) => void;
  } | null>(null);
  const googleRequestInFlightRef = useRef(false);
  const [googleReady, setGoogleReady] = useState(false);

  useEffect(() => {
    if (emailVerifiedToastShown.current) {
      return;
    }
    if (searchParams.get("email_verified") === "1") {
      emailVerifiedToastShown.current = true;
      showToast("info", "Email verified. You can sign in.");
    }
  }, [searchParams, showToast]);

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

  const submitLogin = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void onLogin(username, password);
  };

  return (
    <main className="auth-shell">
      <section className="panel auth-panel auth-login-panel">
        <div>
          <h1 className="app-title">{uiCopy.appTitle}</h1>
          <p className="app-subtitle">Log in to your account</p>
        </div>

        {message ? <div className={`status-banner ${message.tone === "error" ? "error" : ""}`}>{message.text}</div> : null}

        <form className="stack auth-login-form" onSubmit={submitLogin}>
          <label className="field-group">
            <span>Username</span>
            <input
              className="auth-login-input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Email address or username"
              autoComplete="username"
            />
          </label>

          <label className="field-group">
            <span>Password</span>
            <input
              className="auth-login-input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter password"
              autoComplete="current-password"
            />
          </label>

          <div className="button-row auth-login-actions">
            <button type="submit" className="button-primary auth-cta-primary" disabled={disabled}>
              Sign in
            </button>
            <Link to="/auth/register" className="button-secondary auth-cta-secondary auth-button-link">
              Create account
            </Link>
          </div>
        </form>
        {googleClientId ? (
          <button
            type="button"
            className="button-secondary auth-cta-secondary auth-google-button"
            disabled={disabled || !googleReady}
            onClick={() => void startGoogleLogin()}
          >
            Continue with Google
          </button>
        ) : null}

        <Link to="/auth/forgot" className="button-link auth-forgot-password-link">
          Forgot password?
        </Link>
      </section>
      <AuthLegalFooter />
    </main>
  );
}
