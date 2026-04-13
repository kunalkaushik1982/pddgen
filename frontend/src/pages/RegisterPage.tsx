/**
 * Purpose: Dedicated account creation page.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\RegisterPage.tsx
 */

import React, { useState } from "react";
import { Link } from "react-router-dom";

import { AuthLegalFooter } from "../components/legal/AuthLegalFooter";
import { uiCopy } from "../constants/uiCopy";
import { useToast } from "../providers/ToastProvider";

type RegisterPageProps = {
  disabled?: boolean;
  message?: { tone: "info" | "error"; text: string } | null;
  onRegister: (username: string, password: string, email: string) => Promise<void>;
};

export function RegisterPage({ disabled, message, onRegister }: RegisterPageProps): React.JSX.Element {
  const { showToast } = useToast();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [agreedToPolicies, setAgreedToPolicies] = useState(false);

  const submitRegister = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!agreedToPolicies) {
      showToast("error", "Please accept the Terms, Privacy Policy, and refund information to create an account.");
      return;
    }
    void onRegister(username, password, email.trim());
  };

  return (
    <main className="auth-shell">
      <section className="panel auth-panel auth-login-panel">
        <div>
          <h1 className="app-title">{uiCopy.appTitle}</h1>
          <p className="app-subtitle">Create account</p>
        </div>

        {message ? <div className={`status-banner ${message.tone === "error" ? "error" : ""}`}>{message.text}</div> : null}

        <form className="stack auth-login-form" onSubmit={submitRegister}>
          <label className="field-group">
            <span>Username</span>
            <input
              className="auth-login-input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Choose username"
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
              autoComplete="new-password"
            />
          </label>

          <label className="field-group">
            <span>Email</span>
            <input
              className="auth-login-input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
              autoComplete="email"
            />
          </label>

          <label className="register-terms-consent">
            <input
              type="checkbox"
              checked={agreedToPolicies}
              onChange={(event) => setAgreedToPolicies(event.target.checked)}
              aria-required="true"
            />
            <span>
              I agree to the{" "}
              <Link to="/legal/terms">Terms and Conditions</Link> and{" "}
              <Link to="/legal/privacy">Privacy Policy</Link>, and acknowledge the{" "}
              <Link to="/legal/refunds">Cancellation and Refunds</Link> information.
            </span>
          </label>

          <button type="submit" className="button-primary auth-cta-primary" disabled={disabled || !agreedToPolicies}>
            Create account
          </button>
        </form>

        <Link to="/auth" className="button-link auth-forgot-password-link">
          Back to sign in
        </Link>
      </section>
      <AuthLegalFooter />
    </main>
  );
}
