/**
 * Purpose: Shared page shell for navigation and workflow framing.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\layout\AppShell.tsx
 */

import React, { PropsWithChildren, useEffect, useRef, useState } from "react";
import { appConfig } from "../../config/appConfig";
import { applyTheme, clearTheme, resolveThemeId, THEME_STORAGE_KEY } from "../../theme/themeRuntime";

type AppTheme = (typeof appConfig.theme.presets)[number]["id"];

type AppShellProps = PropsWithChildren<{
  title: string;
  subtitle: string;
  statusLabel?: string;
  userLabel?: string;
  userEmail?: string | null;
  activeView?: "workspace" | "history" | "session" | "admin" | "metrics" | "about" | "billing";
  onSelectView?: (view: "workspace" | "history" | "session" | "admin" | "metrics" | "about" | "billing") => void;
  /** Hide workspace/projects/session nav; show admin (and About in menu) only. */
  adminConsoleOnly?: boolean;
  showAdminView?: boolean;
  onOpenMetrics?: () => void;
  onOpenAbout?: () => void;
  onLogout?: () => void;
}>;

export function AppShell({
  children,
  title,
  subtitle,
  statusLabel,
  userLabel,
  userEmail,
  activeView = "workspace",
  onSelectView,
  adminConsoleOnly = false,
  showAdminView = false,
  onOpenMetrics,
  onOpenAbout,
  onLogout,
}: AppShellProps): React.JSX.Element {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [theme, setTheme] = useState<AppTheme>(() => {
    return resolveThemeId(window.localStorage.getItem(THEME_STORAGE_KEY)) as AppTheme;
  });
  const userMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    const preset = appConfig.theme.presets.find((entry) => entry.id === theme) ?? appConfig.theme.presets[0];
    clearTheme(root);
    if (preset) {
      root.setAttribute("data-theme", preset.id);
      applyTheme(root, preset);
    }
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
        <div className="app-header-top">
          <div>
            <h1 className="app-title">{title}</h1>
            <p className="app-subtitle">{subtitle}</p>
          </div>
          
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
                  {userEmail ? (
                    <div className="app-user-menu-field">
                      <span>Email</span>
                      <div className="app-user-menu-value" title={userEmail}>
                        {userEmail}
                      </div>
                    </div>
                  ) : null}
                  <label className="app-user-menu-field">
                    <span>Theme</span>
                    <select value={theme} onChange={(event) => setTheme(event.target.value as AppTheme)}>
                      {appConfig.theme.presets.map((preset) => (
                        <option key={preset.id} value={preset.id}>
                          {preset.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  {onOpenMetrics ? (
                    <button
                      type="button"
                      className="app-user-menu-item"
                      onClick={() => {
                        setIsUserMenuOpen(false);
                        onOpenMetrics();
                      }}
                    >
                      Metrics
                    </button>
                  ) : null}
                  {onOpenAbout ? (
                    <button
                      type="button"
                      className="app-user-menu-item"
                      onClick={() => {
                        setIsUserMenuOpen(false);
                        onOpenAbout();
                      }}
                    >
                      About
                    </button>
                  ) : null}
                  {onSelectView ? (
                    <button
                      type="button"
                      className="app-user-menu-item"
                      onClick={() => {
                        setIsUserMenuOpen(false);
                        onSelectView("billing");
                      }}
                    >
                      Billing
                    </button>
                  ) : null}
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

        {onSelectView ? (
          <div className="app-header-nav">
            {adminConsoleOnly ? null : (
              <>
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

              </>
            )}
            {showAdminView ? (
              <button
                type="button"
                className={activeView === "admin" ? "button-primary" : "button-secondary"}
                onClick={() => onSelectView("admin")}
              >
                Admin
              </button>
            ) : null}
          </div>
        ) : null}
      </header>
      {children}
    </main>
  );
}
