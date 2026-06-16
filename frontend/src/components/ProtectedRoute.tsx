import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { useCurrentUser } from "../hooks/useAuth";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = useAuthStore((s) => s.token);
  const { isLoading, isAuthenticated } = useCurrentUser();

  if (!token) return <Navigate to="/login" replace />;
  if (isLoading) {
    return <div className="flex h-full items-center justify-center text-slate-500">Loading…</div>;
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return <>{children}</>;
}
