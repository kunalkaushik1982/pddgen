type ThemeMode = "dark" | "light";

type ThemePreset = {
  id: string;
  label: string;
  mode: ThemeMode;
};

function normalizeThemeMode(value: unknown): ThemeMode {
  return value === "light" ? "light" : "dark";
}

function normalizeThemePreset(value: unknown): ThemePreset | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const candidate = value as Record<string, unknown>;
  const id = typeof candidate.id === "string" ? candidate.id.trim().toLowerCase() : "";
  const label = typeof candidate.label === "string" ? candidate.label.trim() : "";

  if (!id || !label) {
    return null;
  }

  return {
    id,
    label,
    mode: normalizeThemeMode(candidate.mode),
  };
}

const fallbackThemePresets: ThemePreset[] = [
  { id: "terminal-dark", label: "Terminal Dark", mode: "dark" },
  { id: "terminal-light", label: "Terminal Light", mode: "light" },
  { id: "aurora-green", label: "Aurora Green", mode: "dark" },
  { id: "emerald-obsidian", label: "Emerald Obsidian", mode: "dark" },
  { id: "cyber-matrix", label: "Neon Matrix", mode: "dark" },
];

const themePresets = fallbackThemePresets;
const defaultThemeId = "terminal-dark";

export const appConfig = {
  apiBaseUrlFallback: "http://localhost:8000/api",
  apiOriginFallback: "http://localhost:8000",
  draftSessionPollingMs: 5000,
  toastAutoHideMs: {
    info: 4200,
    error: 6500,
  },
  diagramFitViewDelayMs: 80,
  theme: {
    defaultMode: defaultThemeId,
    presets: themePresets,
  },
} as const;

export type { ThemeMode, ThemePreset };
