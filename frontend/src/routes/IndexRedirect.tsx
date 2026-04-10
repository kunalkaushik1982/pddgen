import React from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "../providers/AuthProvider";

/**
 * Default landing after sign-in: workspace for normal users, admin console for admin-only accounts.
 */
export function IndexRedirect(): React.JSX.Element {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/auth" replace />;
  }
  return <Navigate to={user.adminConsoleOnly ? "/admin" : "/workspace"} replace />;
}
