import React from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { AuthPage } from "../pages/AuthPage";
import { ForgotPasswordPage } from "../pages/ForgotPasswordPage";
import { RegisterPage } from "../pages/RegisterPage";
import { ResetPasswordPage } from "../pages/ResetPasswordPage";
import { useAuth } from "../providers/AuthProvider";
import { useToast } from "../providers/ToastProvider";

export function AuthRoute(): React.JSX.Element {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isLoading, login, loginWithGoogle, register, requestPasswordReset, confirmPasswordReset } = useAuth();
  const { message, showToast } = useToast();

  if (user) {
    return <Navigate to={user.adminConsoleOnly ? "/admin" : "/workspace"} replace />;
  }

  if (location.pathname === "/auth/reset-password") {
    return (
      <ResetPasswordPage
        disabled={isLoading}
        message={message}
        onConfirmPasswordReset={async (token, newPassword) => {
          try {
            await confirmPasswordReset(token, newPassword);
            showToast("info", "Password updated. You can sign in with your new password.");
            navigate("/auth", { replace: true });
          } catch (error) {
            showToast("error", getErrorMessage(error));
          }
        }}
      />
    );
  }

  if (location.pathname === "/auth/forgot") {
    return (
      <ForgotPasswordPage
        disabled={isLoading}
        message={message}
        onRequestPasswordReset={async (email) => {
          try {
            const result = await requestPasswordReset(email);
            if (result.reset_token) {
              showToast("info", `Dev only — reset token: ${result.reset_token}`);
            } else {
              showToast("info", "If an account exists with that verified email, a reset link has been sent.");
            }
          } catch (error) {
            showToast("error", getErrorMessage(error));
          }
        }}
      />
    );
  }

  if (location.pathname === "/auth/register") {
    return (
      <RegisterPage
        disabled={isLoading}
        message={message}
        onRegister={async (username, password, email) => {
          try {
            if (!username.trim()) {
              showToast("error", "Username is required to create an account.");
              return;
            }
            if (!password.trim()) {
              showToast("error", "Password is required to create an account.");
              return;
            }
            if (!email.trim()) {
              showToast("error", "Email is required to create an account.");
              return;
            }
            const nextUser = await register(username, password, email.trim());
            showToast(
              "info",
              nextUser.emailVerified
                ? `Account created for ${nextUser.username}.`
                : `Account created for ${nextUser.username}. Check your email to verify your address.`,
            );
          } catch (error) {
            const message = getErrorMessage(error);
            if (message.includes("Email already registered")) {
              showToast("error", "Email already registered. Please sign in or use Forgot password.");
              return;
            }
            if (message.includes("Username already exists")) {
              showToast("error", "Username already taken. Please choose a different username.");
              return;
            }
            showToast("error", message);
          }
        }}
      />
    );
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
      onGoogleLogin={async (accessToken) => {
        try {
          const nextUser = await loginWithGoogle(accessToken);
          showToast("info", `Signed in as ${nextUser.username}.`);
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
