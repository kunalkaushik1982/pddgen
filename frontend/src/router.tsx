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

const AdminRoute = lazy(async () => {
  const module = await import("./routes/AdminRoute");
  return { default: module.AdminRoute };
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

const IndexRedirect = lazy(async () => {
  const module = await import("./routes/IndexRedirect");
  return { default: module.IndexRedirect };
});

const BillingRoute = lazy(async () => {
  const module = await import("./routes/BillingRoute");
  return { default: module.BillingRoute };
});

const LegalRoute = lazy(async () => {
  const module = await import("./routes/LegalRoute");
  return { default: module.LegalRoute };
});

function RouteLoadingFallback(): React.JSX.Element {
  return (
    <section className="panel">
      <div className="empty-state">Loading application...</div>
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
          <Route path="/auth/reset-password" element={withRouteBoundary("Authentication", <AuthRoute />)} />
          <Route path="/auth/forgot" element={withRouteBoundary("Authentication", <AuthRoute />)} />
          <Route path="/auth/register" element={withRouteBoundary("Authentication", <AuthRoute />)} />
          <Route path="/auth" element={withRouteBoundary("Authentication", <AuthRoute />)} />
          <Route path="/legal/:slug" element={withRouteBoundary("Legal", <LegalRoute />)} />
          <Route element={withRouteBoundary("Application Shell", <AppFrame />)}>
            <Route index element={withRouteBoundary("Home", <IndexRedirect />)} />
            <Route path="/about" element={withRouteBoundary("About", <AboutRoute />)} />
            <Route path="/metrics" element={withRouteBoundary("Metrics", <AdminRoute />)} />
            <Route path="/admin" element={withRouteBoundary("Admin", <AdminRoute />)} />
            <Route path="/workspace" element={withRouteBoundary("Workspace", <WorkspaceRoute />)} />
            <Route path="/projects" element={withRouteBoundary("My Projects", <ProjectsRoute />)} />
            <Route path="/billing" element={withRouteBoundary("Billing", <BillingRoute />)} />
            <Route path="/session" element={withRouteBoundary("Session Detail", <SessionRoute />)} />
            <Route path="/session/:sessionId" element={withRouteBoundary("Session Detail", <SessionRoute />)} />
          </Route>
          <Route path="*" element={<Navigate to="/workspace" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
