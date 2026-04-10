import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";

import { AdminPage } from "../pages/AdminPage";
import { useAuth } from "../providers/AuthProvider";
import { adminService } from "../services/adminService";
import type { AdminPreferences } from "../types/admin";
import { DEFAULT_ADMIN_METRIC_COLUMNS } from "../types/admin";

export function AdminRoute(): React.JSX.Element {
  const { user } = useAuth();
  const queryClient = useQueryClient();
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
  const preferencesQuery = useQuery({
    queryKey: ["admin", "preferences"],
    queryFn: adminService.getPreferences,
    enabled: Boolean(user?.isAdmin),
  });
  const updatePreferencesMutation = useMutation({
    mutationFn: adminService.updatePreferences,
    onMutate: async (columns) => {
      await queryClient.cancelQueries({ queryKey: ["admin", "preferences"] });
      const previousPreferences = queryClient.getQueryData<AdminPreferences>(["admin", "preferences"]);
      queryClient.setQueryData<AdminPreferences>(["admin", "preferences"], {
        sessionMetricsVisibleColumns: columns,
      });
      return { previousPreferences };
    },
    onError: (_error, _columns, context) => {
      if (context?.previousPreferences) {
        queryClient.setQueryData(["admin", "preferences"], context.previousPreferences);
      }
    },
    onSuccess: (preferences) => {
      queryClient.setQueryData(["admin", "preferences"], preferences);
    },
  });

  if (!user?.isAdmin) {
    return <Navigate to={user?.adminConsoleOnly ? "/about" : "/workspace"} replace />;
  }

  return (
    <AdminPage
      users={usersQuery.data ?? []}
      jobs={jobsQuery.data ?? []}
      sessionMetrics={metricsQuery.data ?? []}
      visibleMetricColumns={preferencesQuery.data?.sessionMetricsVisibleColumns ?? DEFAULT_ADMIN_METRIC_COLUMNS}
      onVisibleMetricColumnsChange={async (columns) => updatePreferencesMutation.mutateAsync(columns)}
      isLoading={usersQuery.isLoading || jobsQuery.isLoading || metricsQuery.isLoading || preferencesQuery.isLoading}
    />
  );
}
