/**
 * Purpose: Set a new password using the token from the password-reset email link.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\ResetPasswordPage.tsx
 */

import React, { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AuthLegalFooter } from "../components/legal/AuthLegalFooter";
import { uiCopy } from "../constants/uiCopy";

type ResetPasswordPageProps = {
  disabled?: boolean;
  message?: { tone: "info" | "error"; text: string } | null;
  onConfirmPasswordReset: (token: string, newPassword: string) => Promise<void>;
};

export function ResetPasswordPage({
  disabled,
  message,
  onConfirmPasswordReset,
}: ResetPasswordPageProps): React.JSX.Element {
  const [searchParams] = useSearchParams();
  const tokenFromUrl = searchParams.get("token") ?? "";
  const [newPassword, setNewPassword] = useState("");

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void onConfirmPasswordReset(tokenFromUrl, newPassword);
  };

  return (
    <main className="auth-shell">
      <section className="panel stack auth-panel">
        <div className="section-header-inline">
          <div>
            <h1 className="app-title">{uiCopy.appTitle}</h1>
            <p className="app-subtitle">Choose a new password</p>
          </div>
          <Link to="/auth" className="button-link collapsible-toggle">
            Sign in
          </Link>
        </div>

        {message ? <div className={`status-banner ${message.tone === "error" ? "error" : ""}`}>{message.text}</div> : null}

        {!tokenFromUrl ? (
          <p className="muted">This link is missing a reset token. Open the link from your email, or request a new reset from Forgot password.</p>
        ) : (
          <form className="stack" onSubmit={submit}>
            <label className="field-group">
              <span>New password</span>
              <input
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                placeholder="Enter new password"
                autoComplete="new-password"
              />
            </label>
            <button type="submit" className="button-primary" disabled={disabled}>
              Update password
            </button>
          </form>
        )}

        <Link to="/auth/forgot" className="button-link auth-forgot-password-link">
          Request a new reset link
        </Link>
      </section>
      <AuthLegalFooter />
    </main>
  );
}
