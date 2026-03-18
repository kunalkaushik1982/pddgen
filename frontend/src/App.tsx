/**
 * Purpose: Root application shell for the BA-facing workflow.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\App.tsx
 */

import React from "react";

import { RouteErrorBoundary } from "./components/layout/RouteErrorBoundary";
import { AppRouter } from "./router";

export function App(): React.JSX.Element {
  return (
    <RouteErrorBoundary areaLabel="Application">
      <AppRouter />
    </RouteErrorBoundary>
  );
}
