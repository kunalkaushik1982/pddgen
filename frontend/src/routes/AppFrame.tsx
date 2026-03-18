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

  const activeView =
    location.pathname.startsWith("/projects")
      ? "history"
      : location.pathname.startsWith("/session")
        ? "session"
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
            : uiCopy.workspaceLabel
      }
      userLabel={user.username}
      activeView={activeView}
      onSelectView={(view) => {
        if (view === "history") {
          navigate("/projects");
          return;
        }
        if (view === "session") {
          navigate("/session");
          return;
        }
        navigate("/workspace");
      }}
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
