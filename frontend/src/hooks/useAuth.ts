import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/authStore";
import type { User } from "../types";

/** Resolves the current user from the persisted token. Keeps the auth store's
 *  `user` in sync and tells callers whether auth is still being established. */
export function useCurrentUser() {
  const token = useAuthStore((s) => s.token);
  const setUser = useAuthStore((s) => s.setUser);

  const query = useQuery({
    queryKey: ["me", token],
    queryFn: async () => {
      const user = await api.get<User>("/auth/me");
      setUser(user);
      return user;
    },
    enabled: !!token,
  });

  return {
    user: query.data ?? null,
    isLoading: !!token && query.isLoading,
    isAuthenticated: !!token && !!query.data,
  };
}
