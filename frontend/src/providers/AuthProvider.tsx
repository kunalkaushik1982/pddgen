import React, { createContext, useContext, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authService } from "../services/authService";
import type { User } from "../types/auth";

type AuthContextValue = {
  user: User | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<User>;
  register: (username: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const queryClient = useQueryClient();
  const currentUserQuery = useQuery({
    queryKey: ["auth", "currentUser"],
    queryFn: authService.getCurrentUser,
    retry: false,
  });

  const loginMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) => authService.login(username, password),
    onSuccess: (user) => {
      queryClient.setQueryData(["auth", "currentUser"], user);
    },
  });

  const registerMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) => authService.register(username, password),
    onSuccess: (user) => {
      queryClient.setQueryData(["auth", "currentUser"], user);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: authService.logout,
    onSettled: () => {
      queryClient.setQueryData(["auth", "currentUser"], null);
      void queryClient.invalidateQueries();
    },
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      user: currentUserQuery.data ?? null,
      isLoading: currentUserQuery.isLoading || loginMutation.isPending || registerMutation.isPending || logoutMutation.isPending,
      login: async (username, password) => loginMutation.mutateAsync({ username, password }),
      register: async (username, password) => registerMutation.mutateAsync({ username, password }),
      logout: async () => logoutMutation.mutateAsync(),
    }),
    [
      currentUserQuery.data,
      currentUserQuery.isLoading,
      loginMutation,
      logoutMutation,
      registerMutation,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
