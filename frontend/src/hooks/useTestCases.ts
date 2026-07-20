/**
 * Test case + story AI hooks
 */

"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { testCaseService } from "@/services/testcase.service";
import type { TestCaseGenerateRequest, TestCaseUpdateRequest } from "@/types/testcase";

export const testCaseKeys = {
  all: ["test-cases"] as const,
  lists: () => [...testCaseKeys.all, "list"] as const,
  byStory: (storyId: string) =>
    [...testCaseKeys.lists(), storyId] as const,
  detail: (id: string) => [...testCaseKeys.all, "detail", id] as const,
  analysis: (storyId: string) =>
    [...testCaseKeys.all, "analysis", storyId] as const,
};

export function useStoryTestCases(storyId: string | null) {
  return useQuery({
    queryKey: testCaseKeys.byStory(storyId ?? ""),
    queryFn: () =>
      testCaseService.listByStory(storyId!, { page: 1, page_size: 100 }),
    enabled: Boolean(storyId),
  });
}

export function useTestCase(id: string | null) {
  return useQuery({
    queryKey: testCaseKeys.detail(id ?? ""),
    queryFn: () => testCaseService.getById(id!),
    enabled: Boolean(id),
  });
}

export function useGenerateTestCases() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      storyId,
      payload,
    }: {
      storyId: string;
      payload?: TestCaseGenerateRequest;
    }) => testCaseService.generate(storyId, payload),
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({
        queryKey: testCaseKeys.byStory(vars.storyId),
      });
    },
  });
}

export function useAnalyzeStory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (storyId: string) => testCaseService.analyzeStory(storyId),
    onSuccess: (_data, storyId) => {
      void queryClient.invalidateQueries({
        queryKey: testCaseKeys.analysis(storyId),
      });
    },
  });
}

export function useApproveTestCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => testCaseService.approve(id),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: testCaseKeys.byStory(data.test_case.story_id),
      });
      void queryClient.invalidateQueries({
        queryKey: testCaseKeys.detail(data.test_case.id),
      });
    },
  });
}

export function useRejectTestCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      testCaseService.reject(id, reason),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: testCaseKeys.byStory(data.test_case.story_id),
      });
    },
  });
}

export function useApproveAllTestCases() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (storyId: string) => testCaseService.approveAll(storyId),
    onSuccess: (_data, storyId) => {
      void queryClient.invalidateQueries({
        queryKey: testCaseKeys.byStory(storyId),
      });
    },
  });
}

export function useUpdateTestCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: TestCaseUpdateRequest;
    }) => testCaseService.update(id, payload),
    onSuccess: (tc) => {
      void queryClient.invalidateQueries({
        queryKey: testCaseKeys.byStory(tc.story_id),
      });
      void queryClient.invalidateQueries({
        queryKey: testCaseKeys.detail(tc.id),
      });
    },
  });
}
