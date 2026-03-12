/**
 * Purpose: Shared page shell for navigation and workflow framing.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\layout\AppShell.tsx
 */

import React, { PropsWithChildren } from "react";

type AppShellProps = PropsWithChildren<{
  title: string;
  subtitle: string;
  statusLabel?: string;
}>;

export function AppShell({ children, title, subtitle, statusLabel }: AppShellProps): JSX.Element {
  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <h1 className="app-title">{title}</h1>
          <p className="app-subtitle">{subtitle}</p>
        </div>
        {statusLabel ? <span className="status-chip">{statusLabel}</span> : null}
      </header>
      {children}
    </main>
  );
}
