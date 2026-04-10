import React from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "../providers/AuthProvider";

/**
 * Default landing after sign-in: workspace for normal users, metrics for admin-only accounts.
 */
export function IndexRedirect(): React.JSX.Element {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/auth" replace />;
  }
  return <Navigate to={user.adminConsoleOnly ? "/metrics" : "/workspace"} replace />;
}
