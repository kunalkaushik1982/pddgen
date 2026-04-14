/**
 * Purpose: Simple username/password login and registration page.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\AuthPage.tsx
 */

import React, { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

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
    <div className="auth-shell-dark">
      <div className="auth-box">
        <div>
          <div className="auth-header-logo">
            <div className="auth-header-logo-icon">
              {/* Box with circle inside */}
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="4" />
                <circle cx="12" cy="12" r="4" />
              </svg>
            </div>
          </div>
          <h1 className="auth-header-title">Welcome back</h1>
          <p className="auth-header-subtitle">
            Enter your details to sign in to your<br />workspace.
          </p>
        </div>

        {message ? (
          <div className={`status-banner-dark ${message.tone === "error" ? "error" : ""}`}>
            {message.text}
          </div>
        ) : null}

        <form className="auth-form-dark" onSubmit={submitLogin}>
          <div className="auth-field-dark">
            <label className="auth-label-dark">Email Address</label>
            <div className="auth-input-wrapper">
              <div className="auth-input-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                  <polyline points="22,6 12,13 2,6"/>
                </svg>
              </div>
              <input
                className="auth-input-dark"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="admin@enterprise.com"
                autoComplete="username"
              />
            </div>
          </div>

          <div className="auth-field-dark">
            <div className="auth-label-row">
              <label className="auth-label-dark">Password</label>
              <Link to="/auth/forgot" className="auth-forgot-link">
                Forgot password?
              </Link>
            </div>
            <div className="auth-input-wrapper">
              <div className="auth-input-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
              </div>
              <input
                className="auth-input-dark"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </div>
          </div>

          <button type="submit" className="auth-submit-dark" disabled={disabled}>
            Sign In
          </button>
        </form>

        <div className="auth-divider">Or continue with</div>

        <div className="auth-social-row">
          {googleClientId ? (
            <button
              type="button"
              className="auth-social-btn"
              disabled={disabled || !googleReady}
              onClick={() => void startGoogleLogin()}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Google
            </button>
          ) : (
             <button type="button" className="auth-social-btn" disabled={disabled}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Google
            </button>
          )}
          
          <button type="button" className="auth-social-btn" disabled={disabled}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zM24 11.4H12.6V0H24v11.4z"/>
            </svg>
            Microsoft
          </button>
        </div>

        <div className="auth-footer-text">
          Don't have an account? <Link to="/auth/register" className="auth-footer-link">Contact Sales</Link>
        </div>
      </div>
    </div>
  );
}
