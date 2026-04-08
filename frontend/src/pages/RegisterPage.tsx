/**
 * Purpose: Dedicated account creation page.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\RegisterPage.tsx
 */

import React, { useState } from "react";
import { Link } from "react-router-dom";

import { uiCopy } from "../constants/uiCopy";

type RegisterPageProps = {
  disabled?: boolean;
  message?: { tone: "info" | "error"; text: string } | null;
  onRegister: (username: string, password: string, email: string) => Promise<void>;
};

export function RegisterPage({ disabled, message, onRegister }: RegisterPageProps): React.JSX.Element {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");

  const submitRegister = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
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

          <button type="submit" className="button-primary auth-cta-primary" disabled={disabled}>
            Create account
          </button>
        </form>

        <Link to="/auth" className="button-link auth-forgot-password-link">
          Back to sign in
        </Link>
      </section>
    </main>
  );
}
