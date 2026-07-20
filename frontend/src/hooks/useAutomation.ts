/**
 * Automation hooks — BDD, Playwright, executions
 */

"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { automationService } from "@/services/automation.service";
import type {
  CreateJiraBugRequest,
  ExecutionRunRequest,
} from "@/types/automation";

export const automationKeys = {
  all: ["automation"] as const,
  bdd: (storyId: string) => [...automationKeys.all, "bdd", storyId] as const,
  playwright: (storyId: string) =>
    [...automationKeys.all, "playwright", storyId] as const,
  executions: (filters: Record<string, string | undefined>) =>
    [...automationKeys.all, "executions", filters] as const,
  execution: (id: string) =>
    [...automationKeys.all, "execution", id] as const,
};

export function useStoryBdd(storyId: string | null) {
  return useQuery({
    queryKey: automationKeys.bdd(storyId ?? ""),
    queryFn: () =>
      automationService.listBdd(storyId!, { page: 1, page_size: 20 }),
    enabled: Boolean(storyId),
  });
}

export function useStoryPlaywright(storyId: string | null) {
  return useQuery({
    queryKey: automationKeys.playwright(storyId ?? ""),
    queryFn: () =>
      automationService.listPlaywright(storyId!, { page: 1, page_size: 20 }),
    enabled: Boolean(storyId),
  });
}

export function useExecutions(
  filters: {
    automation_job_id?: string;
    status?: string;
  } = {}
) {
  return useQuery({
    queryKey: automationKeys.executions(filters),
    queryFn: () =>
      automationService.listExecutions({
        page: 1,
        page_size: 50,
        ...filters,
      }),
  });
}

export function useGenerateBdd() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      storyId,
      includeDrafts,
    }: {
      storyId: string;
      includeDrafts?: boolean;
    }) => automationService.generateBdd(storyId, includeDrafts),
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({
        queryKey: automationKeys.bdd(vars.storyId),
      });
    },
  });
}

export function useGeneratePlaywright() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (storyId: string) =>
      automationService.generatePlaywright(storyId),
    onSuccess: (_data, storyId) => {
      void queryClient.invalidateQueries({
        queryKey: automationKeys.playwright(storyId),
      });
    },
  });
}

export function useRunExecution() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ExecutionRunRequest) =>
      automationService.run(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: [...automationKeys.all, "executions"],
      });
    },
  });
}

export function useAnalyzeFailure() {
  return useMutation({
    mutationFn: (executionId: string) =>
      automationService.analyzeFailure(executionId),
  });
}

export function useCreateJiraBug() {
  return useMutation({
    mutationFn: ({
      executionId,
      payload,
    }: {
      executionId: string;
      payload: CreateJiraBugRequest;
    }) => automationService.createJiraBug(executionId, payload),
  });
}
