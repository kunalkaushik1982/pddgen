import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";

import { AdminPage } from "../pages/AdminPage";
import { useAuth } from "../providers/AuthProvider";
import { adminService } from "../services/adminService";

export function AdminRoute(): React.JSX.Element {
  const { user } = useAuth();
  const usersQuery = useQuery({
    queryKey: ["admin", "users"],
    queryFn: adminService.listUsers,
    enabled: Boolean(user?.isAdmin),
  });
  const jobsQuery = useQuery({
    queryKey: ["admin", "jobs"],
    queryFn: adminService.listJobs,
    enabled: Boolean(user?.isAdmin),
  });
  const metricsQuery = useQuery({
    queryKey: ["admin", "metrics", "sessions"],
    queryFn: adminService.listSessionMetrics,
    enabled: Boolean(user?.isAdmin),
  });

  if (!user?.isAdmin) {
    return <Navigate to={user?.adminConsoleOnly ? "/about" : "/workspace"} replace />;
  }

  return (
    <AdminPage
      users={usersQuery.data ?? []}
      jobs={jobsQuery.data ?? []}
      sessionMetrics={metricsQuery.data ?? []}
      isLoading={usersQuery.isLoading || jobsQuery.isLoading || metricsQuery.isLoading}
    />
  );
}
