/**
 * Purpose: Shared page shell for navigation and workflow framing.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\layout\AppShell.tsx
 */

import React, { PropsWithChildren, useEffect, useRef, useState } from "react";

type AppTheme = "midnight" | "graphite" | "ember" | "parchment";

const THEME_STORAGE_KEY = "pdd_generator_theme";

type AppShellProps = PropsWithChildren<{
  title: string;
  subtitle: string;
  statusLabel?: string;
  userLabel?: string;
  activeView?: "workspace" | "history" | "session";
  onSelectView?: (view: "workspace" | "history" | "session") => void;
  onLogout?: () => void;
}>;

export function AppShell({
  children,
  title,
  subtitle,
  statusLabel,
  userLabel,
  activeView = "workspace",
  onSelectView,
  onLogout,
}: AppShellProps): React.JSX.Element {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [theme, setTheme] = useState<AppTheme>(() => {
    const savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    return savedTheme === "graphite" || savedTheme === "ember" || savedTheme === "parchment" ? savedTheme : "midnight";
  });
  const userMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    if (!isUserMenuOpen) {
      return undefined;
    }

    function handlePointerDown(event: MouseEvent): void {
      if (!userMenuRef.current?.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, [isUserMenuOpen]);

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <h1 className="app-title">{title}</h1>
          <p className="app-subtitle">{subtitle}</p>
        </div>
        <div className="app-header-actions">
          {onSelectView ? (
            <div className="button-row app-header-nav">
              <button
                type="button"
                className={activeView === "workspace" ? "button-primary" : "button-secondary"}
                onClick={() => onSelectView("workspace")}
              >
                Workspace
              </button>
              <button
                type="button"
                className={activeView === "history" ? "button-primary" : "button-secondary"}
                onClick={() => onSelectView("history")}
              >
                My Projects
              </button>
              <button
                type="button"
                className={activeView === "session" ? "button-primary" : "button-secondary"}
                onClick={() => onSelectView("session")}
              >
                Session Detail
              </button>
            </div>
          ) : null}
          {(userLabel || onLogout) ? (
            <div className="app-user-menu" ref={userMenuRef}>
              <button
                type="button"
                className="button-secondary app-user-menu-trigger"
                onClick={() => setIsUserMenuOpen((current) => !current)}
              >
                {userLabel ?? "User"}
              </button>
              {isUserMenuOpen ? (
                <div className="app-user-menu-dropdown">
                  <label className="app-user-menu-field">
                    <span>Theme</span>
                    <select value={theme} onChange={(event) => setTheme(event.target.value as AppTheme)}>
                      <option value="midnight">Midnight</option>
                      <option value="graphite">Graphite</option>
                      <option value="ember">Ember</option>
                      <option value="parchment">Parchment</option>
                    </select>
                  </label>
                  {onLogout ? (
                    <button
                      type="button"
                      className="app-user-menu-item"
                      onClick={() => {
                        setIsUserMenuOpen(false);
                        onLogout();
                      }}
                    >
                      Logout
                    </button>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </header>
      {children}
    </main>
  );
}
