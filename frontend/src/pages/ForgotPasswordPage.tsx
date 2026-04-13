/**
 * Purpose: Request a password reset email (verified account email only).
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\ForgotPasswordPage.tsx
 */

import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AuthLegalFooter } from "../components/legal/AuthLegalFooter";
import { uiCopy } from "../constants/uiCopy";

type ForgotPasswordPageProps = {
  disabled?: boolean;
  message?: { tone: "info" | "error"; text: string } | null;
  onRequestPasswordReset: (email: string) => Promise<void>;
};

export function ForgotPasswordPage({
  disabled,
  message,
  onRequestPasswordReset,
}: ForgotPasswordPageProps): React.JSX.Element {
  const [searchParams] = useSearchParams();
  const emailHint = searchParams.get("email") ?? "";
  const [email, setEmail] = useState(emailHint);

  useEffect(() => {
    if (emailHint) {
      setEmail(emailHint);
    }
  }, [emailHint]);

  return (
    <main className="auth-shell">
      <section className="panel stack auth-panel">
        <div className="section-header-inline">
          <div>
            <h1 className="app-title">{uiCopy.appTitle}</h1>
            <p className="app-subtitle">Forgot password</p>
            <p className="muted" style={{ margin: "8px 0 0" }}>
              Enter the verified email on your account. We will send a link to choose a new password.
            </p>
          </div>
          <Link to="/auth" className="button-link collapsible-toggle">
            Sign in
          </Link>
        </div>

        {message ? <div className={`status-banner ${message.tone === "error" ? "error" : ""}`}>{message.text}</div> : null}

        <label className="field-group">
          <span>Account email</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@company.com"
            autoComplete="email"
          />
        </label>

        <button type="button" className="button-primary" disabled={disabled} onClick={() => void onRequestPasswordReset(email.trim())}>
          Send reset link
        </button>

        <p className="muted" style={{ margin: 0, fontSize: "0.9rem" }}>
          After you receive the email, open the link to set a new password. If you signed up with Google only, use Google account recovery
          instead.
        </p>
      </section>
      <AuthLegalFooter />
    </main>
  );
}
