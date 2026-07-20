/**
 * Dashboard Service — Axios client for reporting APIs
 */

import { apiClient } from "@/lib/axios";
import { API_ENDPOINTS } from "@/lib/constants";
import type {
  AiMetrics,
  CoverageStats,
  DashboardQueryParams,
  DashboardSummary,
  ExecutionTrends,
} from "@/types/dashboard";

function cleanParams(
  params: DashboardQueryParams
): Record<string, string | number> {
  const result: Record<string, string | number> = {};
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      result[key] = value as string | number;
    }
  });
  return result;
}

export const dashboardService = {
  async getSummary(
    params: DashboardQueryParams = {}
  ): Promise<DashboardSummary> {
    const { data } = await apiClient.get<DashboardSummary>(
      `${API_ENDPOINTS.DASHBOARD}/summary`,
      { params: cleanParams(params) }
    );
    return data;
  },

  async getExecutionTrends(
    params: DashboardQueryParams = {}
  ): Promise<ExecutionTrends> {
    const { data } = await apiClient.get<ExecutionTrends>(
      `${API_ENDPOINTS.DASHBOARD}/execution-trends`,
      { params: cleanParams(params) }
    );
    return data;
  },

  async getCoverage(
    params: DashboardQueryParams = {}
  ): Promise<CoverageStats> {
    const { data } = await apiClient.get<CoverageStats>(
      `${API_ENDPOINTS.DASHBOARD}/coverage`,
      { params: cleanParams(params) }
    );
    return data;
  },

  async getAiMetrics(
    params: DashboardQueryParams = {}
  ): Promise<AiMetrics> {
    const { data } = await apiClient.get<AiMetrics>(
      `${API_ENDPOINTS.DASHBOARD}/ai-metrics`,
      { params: cleanParams(params) }
    );
    return data;
  },
};
