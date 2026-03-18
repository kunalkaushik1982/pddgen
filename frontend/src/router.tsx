import React, { Suspense, lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { RouteErrorBoundary } from "./components/layout/RouteErrorBoundary";

const AppFrame = lazy(async () => {
  const module = await import("./routes/AppFrame");
  return { default: module.AppFrame };
});

const AuthRoute = lazy(async () => {
  const module = await import("./routes/AuthRoute");
  return { default: module.AuthRoute };
});

const AboutRoute = lazy(async () => {
  const module = await import("./routes/AboutRoute");
  return { default: module.AboutRoute };
});

const ProjectsRoute = lazy(async () => {
  const module = await import("./routes/ProjectsRoute");
  return { default: module.ProjectsRoute };
});

const SessionRoute = lazy(async () => {
  const module = await import("./routes/SessionRoute");
  return { default: module.SessionRoute };
});

const WorkspaceRoute = lazy(async () => {
  const module = await import("./routes/WorkspaceRoute");
  return { default: module.WorkspaceRoute };
});

function RouteLoadingFallback(): React.JSX.Element {
  return (
    <section className="panel">
      <div className="empty-state">Loading route...</div>
    </section>
  );
}

function withRouteBoundary(areaLabel: string, element: React.ReactNode): React.JSX.Element {
  return <RouteErrorBoundary areaLabel={areaLabel}>{element}</RouteErrorBoundary>;
}

export function AppRouter(): React.JSX.Element {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteLoadingFallback />}>
        <Routes>
          <Route path="/auth" element={withRouteBoundary("Authentication", <AuthRoute />)} />
          <Route element={withRouteBoundary("Application Shell", <AppFrame />)}>
            <Route index element={<Navigate to="/workspace" replace />} />
            <Route path="/about" element={withRouteBoundary("About", <AboutRoute />)} />
            <Route path="/workspace" element={withRouteBoundary("Workspace", <WorkspaceRoute />)} />
            <Route path="/projects" element={withRouteBoundary("My Projects", <ProjectsRoute />)} />
            <Route path="/session" element={withRouteBoundary("Session Detail", <SessionRoute />)} />
            <Route path="/session/:sessionId" element={withRouteBoundary("Session Detail", <SessionRoute />)} />
          </Route>
          <Route path="*" element={<Navigate to="/workspace" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
