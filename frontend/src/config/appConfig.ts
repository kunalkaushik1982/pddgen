type ThemeMode = "dark" | "light";

type ThemePreset = {
  id: string;
  label: string;
  mode: ThemeMode;
  primaryStart: string;
  primaryEnd: string;
  accent: string;
  support: string;
};

function normalizeHexColor(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim().replace(/^#/, "");
  if (!/^[0-9a-fA-F]{6}$/.test(trimmed)) {
    return null;
  }
  return `#${trimmed.toUpperCase()}`;
}

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
  const primaryStart = normalizeHexColor(candidate.primaryStart);
  const primaryEnd = normalizeHexColor(candidate.primaryEnd);
  const accent = normalizeHexColor(candidate.accent);
  const support = normalizeHexColor(candidate.support);

  if (!id || !label || !primaryStart || !primaryEnd || !accent || !support) {
    return null;
  }

  return {
    id,
    label,
    mode: normalizeThemeMode(candidate.mode),
    primaryStart,
    primaryEnd,
    accent,
    support,
  };
}

const fallbackThemePresets: ThemePreset[] = [
  {
    id: "midnight",
    label: "Midnight",
    mode: "dark",
    primaryStart: "#7C3AED",
    primaryEnd: "#4F46E5",
    accent: "#9477FF",
    support: "#CDBBFF",
  },
  {
    id: "graphite",
    label: "Graphite",
    mode: "dark",
    primaryStart: "#0F766E",
    primaryEnd: "#2563EB",
    accent: "#5EEAD4",
    support: "#AFD8D8",
  },
  {
    id: "ember",
    label: "Ember",
    mode: "dark",
    primaryStart: "#EA580C",
    primaryEnd: "#DC2626",
    accent: "#FB923C",
    support: "#FDBA74",
  },
  {
    id: "parchment",
    label: "Parchment",
    mode: "light",
    primaryStart: "#B45309",
    primaryEnd: "#0F766E",
    accent: "#A16207",
    support: "#F0D7A8",
  },
];

function parseThemePresets(rawValue: string | undefined): ThemePreset[] {
  if (!rawValue) {
    return fallbackThemePresets;
  }

  try {
    const parsed = JSON.parse(rawValue);
    if (!Array.isArray(parsed)) {
      return fallbackThemePresets;
    }
    const presets = parsed.map(normalizeThemePreset).filter((preset): preset is ThemePreset => Boolean(preset));
    return presets.length > 0 ? presets : fallbackThemePresets;
  } catch {
    return fallbackThemePresets;
  }
}

const themePresets = parseThemePresets(import.meta.env.VITE_THEME_PRESETS);
const configuredThemeMode = String(import.meta.env.VITE_THEME_MODE ?? "").trim().toLowerCase();
const defaultThemeId = themePresets.some((preset) => preset.id === configuredThemeMode) ? configuredThemeMode : themePresets[0]?.id ?? "midnight";

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
