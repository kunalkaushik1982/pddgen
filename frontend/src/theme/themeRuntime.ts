import { appConfig, type ThemePreset } from "../config/appConfig";

export const THEME_STORAGE_KEY = "pdd_generator_theme";

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
  "--button-primary-text",
  "--button-primary-start",
  "--button-primary-end",
  "--button-primary-shadow",
  "--accent-border",
  "--status-info-text",
  "--status-success-text",
  "--status-warning-text",
  "--status-error-text",
  "--status-info-bg",
  "--status-success-bg",
  "--status-warning-bg",
  "--status-error-bg",
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

function mixHex(hexA: string, hexB: string): string {
  const a = hexToRgb(hexA);
  const b = hexToRgb(hexB);
  const mix = (left: number, right: number) => Math.round((left + right) / 2);
  return `#${[mix(a.r, b.r), mix(a.g, b.g), mix(a.b, b.b)]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("")
    .toUpperCase()}`;
}

function readableTextForBackground(hex: string): string {
  const { r, g, b } = hexToRgb(hex);
  const luminance = (0.299 * r) + (0.587 * g) + (0.114 * b);
  return luminance >= 162 ? "#14212B" : "#F4FBFF";
}

export function resolveThemeId(savedTheme: string | null | undefined): string {
  if (savedTheme && appConfig.theme.presets.some((preset) => preset.id === savedTheme)) {
    return savedTheme;
  }
  return appConfig.theme.defaultMode;
}

export function clearTheme(root: HTMLElement): void {
  THEME_VARIABLES.forEach((variableName) => root.style.removeProperty(variableName));
  root.style.removeProperty("color-scheme");
}

export function applyTheme(root: HTMLElement, preset: ThemePreset): void {
  const isLight = preset.mode === "light";
  const primaryMid = mixHex(preset.primaryStart, preset.primaryEnd);

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
  root.style.setProperty("--button-primary-text", readableTextForBackground(primaryMid));
  root.style.setProperty("--button-primary-start", preset.primaryStart);
  root.style.setProperty("--button-primary-end", preset.primaryEnd);
  root.style.setProperty("--button-primary-shadow", withAlpha(preset.primaryStart, isLight ? 0.22 : 0.35));
  root.style.setProperty("--accent-border", withAlpha(preset.accent, isLight ? 0.24 : 0.3));
  root.style.setProperty("--status-info-text", isLight ? "#1D4ED8" : "#60A5FA");
  root.style.setProperty("--status-success-text", isLight ? "#166534" : "#4ADE80");
  root.style.setProperty("--status-warning-text", isLight ? "#92400E" : "#FBBF24");
  root.style.setProperty("--status-error-text", isLight ? "#B91C1C" : "#F87171");
  root.style.setProperty("--status-info-bg", isLight ? "rgba(37, 99, 235, 0.12)" : "rgba(37, 99, 235, 0.16)");
  root.style.setProperty("--status-success-bg", isLight ? "rgba(22, 163, 74, 0.12)" : "rgba(22, 163, 74, 0.16)");
  root.style.setProperty("--status-warning-bg", isLight ? "rgba(217, 119, 6, 0.12)" : "rgba(217, 119, 6, 0.14)");
  root.style.setProperty("--status-error-bg", isLight ? "rgba(220, 38, 38, 0.12)" : "rgba(220, 38, 38, 0.14)");
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

export function bootstrapTheme(): string {
  const root = document.documentElement;
  const themeId = resolveThemeId(window.localStorage.getItem(THEME_STORAGE_KEY));
  const preset = appConfig.theme.presets.find((entry) => entry.id === themeId) ?? appConfig.theme.presets[0];
  clearTheme(root);
  if (preset) {
    root.setAttribute("data-theme", preset.id);
    applyTheme(root, preset);
  }
  window.localStorage.setItem(THEME_STORAGE_KEY, themeId);
  return themeId;
}
