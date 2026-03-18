export const appConfig = {
  apiBaseUrlFallback: "http://localhost:8000/api",
  apiOriginFallback: "http://localhost:8000",
  draftSessionPollingMs: 5000,
  toastAutoHideMs: {
    info: 4200,
    error: 6500,
  },
  diagramFitViewDelayMs: 80,
} as const;
