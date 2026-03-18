/**
 * Purpose: Simple username/password login and registration page.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\pages\AuthPage.tsx
 */

import React, { useState } from "react";

type AuthPageProps = {
  disabled?: boolean;
  message?: { tone: "info" | "error"; text: string } | null;
  onLogin: (username: string, password: string) => Promise<void>;
  onRegister: (username: string, password: string) => Promise<void>;
};

export function AuthPage({ disabled, message, onLogin, onRegister }: AuthPageProps): React.JSX.Element {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  return (
    <main className="auth-shell">
      <section className="panel stack auth-panel">
        <div>
          <h1 className="app-title">BA Process Copilot</h1>
          <p className="app-subtitle">Sign in to create new runs and reopen previous ones.</p>
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
      </section>
    </main>
  );
}
