import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";

import { AdminPage } from "../pages/AdminPage";
import { useAuth } from "../providers/AuthProvider";
import { metricsService } from "../services/metricsService";
import type { AdminPreferences } from "../types/admin";
import { DEFAULT_ADMIN_METRIC_COLUMNS } from "../types/admin";

export function AdminRoute(): React.JSX.Element {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const preferencesQuery = useQuery({
    queryKey: ["metrics", "preferences"],
    queryFn: metricsService.getPreferences,
    enabled: Boolean(user),
  });
  const selectedOwnerId = user?.isAdmin
    ? preferencesQuery.data?.metricsSelectedOwnerId ?? "all"
    : user?.username ?? null;
  const jobsQuery = useQuery({
    queryKey: ["metrics", "jobs", selectedOwnerId],
    queryFn: () => metricsService.listJobs(selectedOwnerId),
    enabled: Boolean(user),
  });
  const metricsQuery = useQuery({
    queryKey: ["metrics", "sessions", selectedOwnerId],
    queryFn: () => metricsService.listSessionMetrics(selectedOwnerId),
    enabled: Boolean(user),
  });
  const ownersQuery = useQuery({
    queryKey: ["metrics", "owners"],
    queryFn: metricsService.listOwners,
    enabled: Boolean(user?.isAdmin),
  });
  const updatePreferencesMutation = useMutation({
    mutationFn: metricsService.updatePreferences,
    onMutate: async (preferences) => {
      await queryClient.cancelQueries({ queryKey: ["metrics", "preferences"] });
      const previousPreferences = queryClient.getQueryData<AdminPreferences>(["metrics", "preferences"]);
      queryClient.setQueryData<AdminPreferences>(["metrics", "preferences"], preferences);
      return { previousPreferences };
    },
    onError: (_error, _preferences, context) => {
      if (context?.previousPreferences) {
        queryClient.setQueryData(["metrics", "preferences"], context.previousPreferences);
      }
    },
    onSuccess: (preferences) => {
      queryClient.setQueryData(["metrics", "preferences"], preferences);
    },
  });

  if (!user) {
    return <Navigate to="/auth" replace />;
  }

  const currentPreferences: AdminPreferences = {
    sessionMetricsVisibleColumns: preferencesQuery.data?.sessionMetricsVisibleColumns ?? DEFAULT_ADMIN_METRIC_COLUMNS,
    metricsSelectedOwnerId: selectedOwnerId,
  };

  return (
    <AdminPage
      users={[]}
      jobs={jobsQuery.data ?? []}
      sessionMetrics={metricsQuery.data ?? []}
      visibleMetricColumns={currentPreferences.sessionMetricsVisibleColumns}
      onVisibleMetricColumnsChange={async (columns) =>
        updatePreferencesMutation.mutateAsync({
          ...currentPreferences,
          sessionMetricsVisibleColumns: columns,
        })
      }
      ownerOptions={ownersQuery.data ?? []}
      selectedOwnerId={currentPreferences.metricsSelectedOwnerId}
      onSelectedOwnerIdChange={
        user.isAdmin
          ? async (ownerId) =>
              updatePreferencesMutation.mutateAsync({
                ...currentPreferences,
                metricsSelectedOwnerId: ownerId,
              })
          : undefined
      }
      isAdminView={user.isAdmin}
      isLoading={preferencesQuery.isLoading || jobsQuery.isLoading || metricsQuery.isLoading || ownersQuery.isLoading}
    />
  );
}
