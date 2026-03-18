import React from "react";

import { AuthProvider } from "./AuthProvider";
import { QueryProvider } from "./QueryProvider";
import { ToastProvider } from "./ToastProvider";
import { WorkspaceDraftProvider } from "./WorkspaceDraftProvider";

export function AppProviders({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <QueryProvider>
      <AuthProvider>
        <ToastProvider>
          <WorkspaceDraftProvider>{children}</WorkspaceDraftProvider>
        </ToastProvider>
      </AuthProvider>
    </QueryProvider>
  );
}
