import { appConfig, type ThemePreset } from "../config/appConfig";

export const THEME_STORAGE_KEY = "pdd_generator_theme";

export function resolveThemeId(savedTheme: string | null | undefined): string {
  if (savedTheme && appConfig.theme.presets.some((preset) => preset.id === savedTheme)) {
    return savedTheme;
  }
  return appConfig.theme.defaultMode;
}

export function clearTheme(root: HTMLElement): void {
  // Legacy cleanup if transitioning from JS-based CSS variables
  root.removeAttribute("data-theme");
  root.style.cssText = "";
}

export function applyTheme(root: HTMLElement, preset: ThemePreset): void {
  root.setAttribute("data-theme", preset.id);
  // Optional: Set strict color-scheme matching for browser native components
  root.style.setProperty("color-scheme", preset.mode);
}

export function bootstrapTheme(): string {
  const root = document.documentElement;
  const themeId = resolveThemeId(window.localStorage.getItem(THEME_STORAGE_KEY));
  const preset = appConfig.theme.presets.find((entry) => entry.id === themeId) ?? appConfig.theme.presets[0]!;
  
  clearTheme(root);
  applyTheme(root, preset);
  
  window.localStorage.setItem(THEME_STORAGE_KEY, themeId);
  return themeId;
}
