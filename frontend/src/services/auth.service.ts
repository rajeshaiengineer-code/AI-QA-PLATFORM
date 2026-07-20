/**
 * Authentication Service
 * Handles user authentication, login, logout, token management
 */

import { apiClient } from "@/lib/axios";
import {
  clearAuthData,
  getRefreshToken,
  removeToken,
  setRefreshToken,
  setToken,
} from "@/lib/auth";
import { API_ENDPOINTS } from "@/lib/constants";
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
} from "@/types/auth";

interface TokenApiResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    email: string;
    full_name: string;
    is_active: boolean;
    is_superuser: boolean;
    memberships: Array<{
      id: string;
      organization_id: string;
      organization_name?: string | null;
      organization_slug?: string | null;
      role: string;
    }>;
    created_at?: string;
    updated_at?: string;
  };
}

function mapUser(raw: TokenApiResponse["user"]): User {
  const primaryRole = raw.memberships[0]?.role ?? "viewer";
  return {
    id: raw.id,
    email: raw.email,
    name: raw.full_name,
    role: primaryRole as User["role"],
    createdAt: raw.created_at ?? "",
    updatedAt: raw.updated_at ?? "",
  };
}

function toLoginResponse(data: TokenApiResponse): LoginResponse {
  return {
    user: mapUser(data.user),
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
  };
}

export const authService = {
  async login(payload: LoginRequest): Promise<LoginResponse> {
    const { data } = await apiClient.post<TokenApiResponse>(
      API_ENDPOINTS.AUTH.LOGIN,
      payload
    );
    setToken(data.access_token);
    setRefreshToken(data.refresh_token);
    return toLoginResponse(data);
  },

  async register(payload: RegisterRequest): Promise<LoginResponse> {
    const { data } = await apiClient.post<TokenApiResponse>(
      "/auth/register",
      {
        email: payload.email,
        password: payload.password,
        full_name: payload.name,
      }
    );
    setToken(data.access_token);
    setRefreshToken(data.refresh_token);
    return toLoginResponse(data);
  },

  async me(): Promise<User> {
    const { data } = await apiClient.get<TokenApiResponse["user"]>("/auth/me");
    return mapUser(data);
  },

  async refresh(): Promise<LoginResponse> {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      throw new Error("No refresh token");
    }
    const { data } = await apiClient.post<TokenApiResponse>(
      API_ENDPOINTS.AUTH.REFRESH,
      { refresh_token: refreshToken }
    );
    setToken(data.access_token);
    setRefreshToken(data.refresh_token);
    return toLoginResponse(data);
  },

  logout(): void {
    removeToken();
    clearAuthData();
  },
};
