import React from "react";
import { Navigate } from "react-router-dom";

import { AuthPage } from "../pages/AuthPage";
import { useAuth } from "../providers/AuthProvider";
import { useToast } from "../providers/ToastProvider";

export function AuthRoute(): React.JSX.Element {
  const { user, isLoading, login, loginWithGoogle, register, requestPasswordReset, confirmPasswordReset } = useAuth();
  const { message, showToast } = useToast();

  if (user) {
    return <Navigate to="/workspace" replace />;
  }

  return (
    <AuthPage
      disabled={isLoading}
      message={message}
      onLogin={async (username, password) => {
        try {
          const nextUser = await login(username, password);
          showToast("info", `Signed in as ${nextUser.username}.`);
        } catch (error) {
          showToast("error", getErrorMessage(error));
        }
      }}
      onRegister={async (username, password) => {
        try {
          const nextUser = await register(username, password);
          showToast("info", `Account created for ${nextUser.username}.`);
        } catch (error) {
          showToast("error", getErrorMessage(error));
        }
      }}
      onGoogleLogin={async (idToken) => {
        try {
          const nextUser = await loginWithGoogle(idToken);
          showToast("info", `Signed in as ${nextUser.username}.`);
        } catch (error) {
          showToast("error", getErrorMessage(error));
        }
      }}
      onRequestPasswordReset={async (username) => {
        try {
          const result = await requestPasswordReset(username);
          if (result.reset_token) {
            showToast("info", `Reset token: ${result.reset_token}`);
          } else {
            showToast("info", "If the account exists, a password reset token has been issued.");
          }
        } catch (error) {
          showToast("error", getErrorMessage(error));
        }
      }}
      onConfirmPasswordReset={async (token, newPassword) => {
        try {
          await confirmPasswordReset(token, newPassword);
          showToast("info", "Password reset successful. You can sign in with your new password.");
        } catch (error) {
          showToast("error", getErrorMessage(error));
        }
      }}
    />
  );
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "An unexpected error occurred.";
}
