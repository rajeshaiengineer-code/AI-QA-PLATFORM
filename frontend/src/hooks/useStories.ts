/**
 * Story hooks — TanStack Query wrappers around storyService
 */

"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import axios from "axios";

import { storyService } from "@/services/story.service";
import type { StoryFilters } from "@/store/story.store";
import type { CreateStoryRequest, UpdateStoryRequest } from "@/types/story";

export const storyKeys = {
  all: ["stories"] as const,
  lists: () => [...storyKeys.all, "list"] as const,
  list: (filters: StoryFilters) => [...storyKeys.lists(), filters] as const,
  details: () => [...storyKeys.all, "detail"] as const,
  detail: (id: string) => [...storyKeys.details(), id] as const,
};

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { error?: { message?: string }; detail?: string }
      | undefined;
    return (
      data?.error?.message ||
      data?.detail ||
      error.message ||
      "Request failed"
    );
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}

export function useStoriesQuery(filters: StoryFilters) {
  return useQuery({
    queryKey: storyKeys.list(filters),
    queryFn: () =>
      storyService.list({
        page: filters.page,
        page_size: filters.page_size,
        status: filters.status || undefined,
        story_type: filters.story_type || undefined,
        priority: filters.priority || undefined,
        project_id: filters.project_id || undefined,
        sprint_id: filters.sprint_id || undefined,
        search: filters.search || undefined,
      }),
    placeholderData: (previous) => previous,
  });
}

export function useStoryQuery(id: string | null) {
  return useQuery({
    queryKey: storyKeys.detail(id ?? ""),
    queryFn: () => storyService.getById(id!),
    enabled: Boolean(id),
  });
}

export function useCreateStory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateStoryRequest) => storyService.create(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: storyKeys.lists() });
    },
  });
}

export function useUpdateStory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateStoryRequest }) =>
      storyService.update(id, payload),
    onSuccess: (story) => {
      void queryClient.invalidateQueries({ queryKey: storyKeys.lists() });
      void queryClient.invalidateQueries({
        queryKey: storyKeys.detail(story.id),
      });
    },
  });
}

export function useDeleteStory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => storyService.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: storyKeys.lists() });
    },
  });
}
