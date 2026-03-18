import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

import type { WorkflowMessage } from "../types/workflow";

type ToastContextValue = {
  message: WorkflowMessage | null;
  showToast: (tone: WorkflowMessage["tone"], text: string) => void;
  clearToast: () => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [message, setMessage] = useState<WorkflowMessage | null>(null);

  useEffect(() => {
    if (!message) {
      return undefined;
    }

    const timeoutMs = message.tone === "error" ? 6500 : 4200;
    const timeoutId = window.setTimeout(() => {
      setMessage((current) => (current === message ? null : current));
    }, timeoutMs);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [message]);

  const value = useMemo<ToastContextValue>(
    () => ({
      message,
      showToast: (tone, text) => setMessage({ tone, text }),
      clearToast: () => setMessage(null),
    }),
    [message],
  );

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider.");
  }
  return context;
}
