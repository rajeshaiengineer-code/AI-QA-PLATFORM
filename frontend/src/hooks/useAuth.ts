/**
 * useAuth Hook
 * Handles authentication state and operations
 */

"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";

import { ROUTES } from "@/lib/constants";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/auth.store";
import type { LoginRequest } from "@/types/auth";

export function useAuth() {
  const router = useRouter();
  const { user, isAuthenticated, setUser, logout: clearStore } = useAuthStore();

  const login = useCallback(
    async (credentials: LoginRequest) => {
      const result = await authService.login(credentials);
      setUser({
        id: result.user.id,
        email: result.user.email,
        name: result.user.name,
        role: String(result.user.role),
      });
      router.push(ROUTES.DASHBOARD);
      return result;
    },
    [router, setUser]
  );

  const logout = useCallback(async () => {
    authService.logout();
    clearStore();
    router.push(ROUTES.LOGIN);
  }, [clearStore, router]);

  return {
    user,
    isAuthenticated,
    login,
    logout,
  };
}
