/**
 * Purpose: Shared page shell for navigation and workflow framing.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\layout\AppShell.tsx
 */

import React, { PropsWithChildren, useEffect, useRef, useState } from "react";
import { appConfig, type ThemePreset } from "../../config/appConfig";

const THEME_STORAGE_KEY = "pdd_generator_theme";
const THEME_VARIABLES = [
  "--app-text",
  "--app-muted",
  "--app-bg",
  "--panel-bg",
  "--panel-border",
  "--panel-shadow",
  "--surface-soft",
  "--surface-strong",
  "--surface-card",
  "--overlay-bg",
  "--preview-bg",
  "--preview-bg-strong",
  "--button-secondary-bg",
  "--button-secondary-text",
  "--button-primary-start",
  "--button-primary-end",
  "--button-primary-shadow",
  "--accent-border",
  "--summary-card-bg",
  "--summary-card-text",
  "--summary-card-subtle",
  "--toast-info-bg",
  "--toast-info-text",
  "--toast-info-border",
  "--toast-error-bg",
  "--toast-error-text",
  "--toast-error-border",
] as const;

type AppTheme = (typeof appConfig.theme.presets)[number]["id"];

type AppShellProps = PropsWithChildren<{
  title: string;
  subtitle: string;
  statusLabel?: string;
  userLabel?: string;
  activeView?: "workspace" | "history" | "session" | "admin" | "about";
  onSelectView?: (view: "workspace" | "history" | "session" | "admin" | "about") => void;
  showAdminView?: boolean;
  onOpenAbout?: () => void;
  onLogout?: () => void;
}>;

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const normalized = hex.replace("#", "");
  return {
    r: Number.parseInt(normalized.slice(0, 2), 16),
    g: Number.parseInt(normalized.slice(2, 4), 16),
    b: Number.parseInt(normalized.slice(4, 6), 16),
  };
}

function withAlpha(hex: string, alpha: number): string {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function applyTheme(root: HTMLElement, preset: ThemePreset): void {
  const isLight = preset.mode === "light";

  root.style.setProperty("color-scheme", preset.mode);
  root.style.setProperty("--app-text", isLight ? "#14212B" : "#F4FBFF");
  root.style.setProperty("--app-muted", isLight ? "#4C6271" : "#BED0DB");
  root.style.setProperty(
    "--app-bg",
    isLight
      ? `radial-gradient(circle at top left, ${withAlpha(preset.primaryStart, 0.14)}, transparent 28%),
         radial-gradient(circle at top right, ${withAlpha(preset.support, 0.14)}, transparent 24%),
         linear-gradient(180deg, #FBFFFE 0%, #FFF8F1 100%)`
      : `radial-gradient(circle at top left, ${withAlpha(preset.primaryStart, 0.22)}, transparent 28%),
         radial-gradient(circle at top right, ${withAlpha(preset.support, 0.18)}, transparent 24%),
         linear-gradient(180deg, #111A20 0%, #0A1014 100%)`,
  );
  root.style.setProperty("--panel-bg", isLight ? "rgba(255, 255, 255, 0.9)" : "rgba(16, 24, 30, 0.9)");
  root.style.setProperty("--panel-border", withAlpha(preset.accent, isLight ? 0.18 : 0.24));
  root.style.setProperty("--panel-shadow", isLight ? "0 18px 48px rgba(26, 39, 49, 0.12)" : "0 18px 48px rgba(0, 0, 0, 0.32)");
  root.style.setProperty("--surface-soft", isLight ? "rgba(255, 255, 255, 0.94)" : "rgba(17, 26, 33, 0.9)");
  root.style.setProperty("--surface-strong", isLight ? "rgba(255, 255, 255, 0.98)" : "rgba(14, 22, 28, 0.98)");
  root.style.setProperty("--surface-card", isLight ? "rgba(255, 255, 255, 0.96)" : "rgba(15, 22, 28, 0.94)");
  root.style.setProperty("--overlay-bg", isLight ? "rgba(20, 34, 46, 0.18)" : "rgba(5, 11, 15, 0.68)");
  root.style.setProperty("--preview-bg", isLight ? "#F5FBFC" : "#102028");
  root.style.setProperty("--preview-bg-strong", isLight ? "#F1FBF5" : "#0F1A21");
  root.style.setProperty("--button-secondary-bg", isLight ? withAlpha(preset.support, 0.22) : withAlpha(preset.support, 0.18));
  root.style.setProperty("--button-secondary-text", isLight ? "#14212B" : "#F4FBFF");
  root.style.setProperty("--button-primary-start", preset.primaryStart);
  root.style.setProperty("--button-primary-end", preset.primaryEnd);
  root.style.setProperty("--button-primary-shadow", withAlpha(preset.primaryStart, isLight ? 0.22 : 0.35));
  root.style.setProperty("--accent-border", withAlpha(preset.accent, isLight ? 0.24 : 0.3));
  root.style.setProperty("--summary-card-bg", "rgba(255, 255, 255, 0.98)");
  root.style.setProperty("--summary-card-text", "#14212B");
  root.style.setProperty("--summary-card-subtle", isLight ? "#4C6271" : "#365061");
  root.style.setProperty("--toast-info-bg", isLight ? "rgba(255, 255, 255, 0.98)" : withAlpha(preset.primaryStart, 0.18));
  root.style.setProperty("--toast-info-text", "#14212B");
  root.style.setProperty("--toast-info-border", withAlpha(preset.primaryStart, isLight ? 0.28 : 0.32));
  root.style.setProperty("--toast-error-bg", isLight ? "rgba(255, 247, 243, 0.98)" : withAlpha(preset.support, 0.22));
  root.style.setProperty("--toast-error-text", isLight ? "#6B2D1A" : "#FFE9E2");
  root.style.setProperty("--toast-error-border", withAlpha(preset.support, isLight ? 0.28 : 0.32));
}

function clearTheme(root: HTMLElement): void {
  THEME_VARIABLES.forEach((variableName) => root.style.removeProperty(variableName));
  root.style.removeProperty("color-scheme");
}

export function AppShell({
  children,
  title,
  subtitle,
  statusLabel,
  userLabel,
  activeView = "workspace",
  onSelectView,
  showAdminView = false,
  onOpenAbout,
  onLogout,
}: AppShellProps): React.JSX.Element {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [theme, setTheme] = useState<AppTheme>(() => {
    const savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (savedTheme && appConfig.theme.presets.some((preset) => preset.id === savedTheme)) {
      return savedTheme as AppTheme;
    }
    return appConfig.theme.defaultMode as AppTheme;
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
                      {appConfig.theme.presets.map((preset) => (
                        <option key={preset.id} value={preset.id}>
                          {preset.label}
                        </option>
                      ))}
                    </select>
                  </label>
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
