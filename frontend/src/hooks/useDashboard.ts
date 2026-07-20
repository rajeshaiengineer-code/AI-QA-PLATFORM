/**
 * Dashboard hooks — TanStack Query wrappers around dashboardService
 */

"use client";

import { useQuery } from "@tanstack/react-query";

import { getErrorMessage } from "@/hooks/useStories";
import { dashboardService } from "@/services/dashboard.service";
import type { DashboardQueryParams } from "@/types/dashboard";

export { getErrorMessage };

export const dashboardKeys = {
  all: ["dashboard"] as const,
  summary: (params: DashboardQueryParams) =>
    [...dashboardKeys.all, "summary", params] as const,
  trends: (params: DashboardQueryParams) =>
    [...dashboardKeys.all, "trends", params] as const,
  coverage: (params: DashboardQueryParams) =>
    [...dashboardKeys.all, "coverage", params] as const,
  aiMetrics: (params: DashboardQueryParams) =>
    [...dashboardKeys.all, "ai-metrics", params] as const,
};

export function useDashboardSummaryQuery(params: DashboardQueryParams = {}) {
  return useQuery({
    queryKey: dashboardKeys.summary(params),
    queryFn: () => dashboardService.getSummary(params),
  });
}

export function useExecutionTrendsQuery(params: DashboardQueryParams = {}) {
  return useQuery({
    queryKey: dashboardKeys.trends(params),
    queryFn: () => dashboardService.getExecutionTrends(params),
  });
}

export function useCoverageQuery(params: DashboardQueryParams = {}) {
  return useQuery({
    queryKey: dashboardKeys.coverage(params),
    queryFn: () => dashboardService.getCoverage(params),
  });
}

export function useAiMetricsQuery(params: DashboardQueryParams = {}) {
  return useQuery({
    queryKey: dashboardKeys.aiMetrics(params),
    queryFn: () => dashboardService.getAiMetrics(params),
  });
}
