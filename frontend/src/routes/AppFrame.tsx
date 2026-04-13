import React from "react";
import { Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";

import { AppShell } from "../components/layout/AppShell";
import { uiCopy } from "../constants/uiCopy";
import { useAuth } from "../providers/AuthProvider";
import { useToast } from "../providers/ToastProvider";

export function AppFrame(): React.JSX.Element {
  const { user, isLoading, logout } = useAuth();
  const { message } = useToast();
  const location = useLocation();
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <AppShell title={uiCopy.appTitle} subtitle={uiCopy.loadingSessionSubtitle} activeView="workspace">
        <section className="panel">
          <div className="empty-state">{uiCopy.loadingApplicationMessage}</div>
        </section>
      </AppShell>
    );
  }

  if (!user) {
    return <Navigate to="/auth" replace />;
  }

  if (
    user.adminConsoleOnly &&
    !location.pathname.startsWith("/admin") &&
    !location.pathname.startsWith("/metrics") &&
    !location.pathname.startsWith("/about") &&
    !location.pathname.startsWith("/billing")
  ) {
    return <Navigate to="/metrics" replace />;
  }

  const activeView =
    location.pathname.startsWith("/projects")
      ? "history"
      : location.pathname.startsWith("/metrics")
        ? "metrics"
      : location.pathname.startsWith("/admin")
        ? "admin"
      : location.pathname.startsWith("/about")
        ? "about"
      : location.pathname.startsWith("/session")
        ? "session"
      : location.pathname.startsWith("/billing")
        ? "billing"
        : "workspace";

  return (
    <AppShell
      title={uiCopy.appTitle}
      subtitle={uiCopy.appSubtitle}
      statusLabel={
        activeView === "history"
          ? uiCopy.projectsLabel
          : activeView === "session"
            ? uiCopy.sessionDetailLabel
            : activeView === "metrics"
              ? uiCopy.metricsLabel
            : activeView === "admin"
              ? uiCopy.adminLabel
            : activeView === "about"
              ? uiCopy.aboutLabel
            : activeView === "billing"
              ? uiCopy.billingLabel
            : uiCopy.workspaceLabel
      }
      userLabel={user.username}
      userEmail={user.email ?? null}
      activeView={activeView}
      adminConsoleOnly={Boolean(user.adminConsoleOnly)}
      showAdminView={user.isAdmin}
      onSelectView={(view) => {
        if (view === "history") {
          navigate("/projects");
          return;
        }
        if (view === "admin") {
          navigate("/metrics");
          return;
        }
        if (view === "metrics") {
          navigate("/metrics");
          return;
        }
        if (view === "session") {
          navigate("/session");
          return;
        }
        if (view === "about") {
          navigate("/about");
          return;
        }
        if (view === "billing") {
          navigate("/billing");
          return;
        }
        navigate("/workspace");
      }}
      onOpenMetrics={() => navigate("/metrics")}
      onOpenAbout={() => navigate("/about")}
      onLogout={() => void logout()}
    >
      {message ? (
        <div
          className={`status-toast ${message.tone === "error" ? "status-toast-error" : "status-toast-info"}`}
          role={message.tone === "error" ? "alert" : "status"}
          aria-live={message.tone === "error" ? "assertive" : "polite"}
          aria-atomic="true"
        >
          {message.text}
        </div>
      ) : null}
      <Outlet />
    </AppShell>
  );
}
