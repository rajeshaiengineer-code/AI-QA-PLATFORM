/**
 * Sprint hooks — TanStack Query wrappers around sprintService
 */

"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { getErrorMessage } from "@/hooks/useStories";
import { sprintService } from "@/services/sprint.service";
import type { SprintFilters } from "@/store/sprint.store";
import type { CreateSprintRequest, UpdateSprintRequest } from "@/types/sprint";

export { getErrorMessage };

export const sprintKeys = {
  all: ["sprints"] as const,
  lists: () => [...sprintKeys.all, "list"] as const,
  list: (filters: SprintFilters) => [...sprintKeys.lists(), filters] as const,
  details: () => [...sprintKeys.all, "detail"] as const,
  detail: (id: string) => [...sprintKeys.details(), id] as const,
};

export function useSprintsQuery(filters: SprintFilters) {
  return useQuery({
    queryKey: sprintKeys.list(filters),
    queryFn: () =>
      sprintService.list({
        page: filters.page,
        page_size: filters.page_size,
        project_id: filters.project_id || undefined,
        is_active:
          filters.is_active === ""
            ? undefined
            : filters.is_active === "true"
              ? true
              : filters.is_active === "false"
                ? false
                : undefined,
        search: filters.search || undefined,
      }),
    placeholderData: (previous) => previous,
  });
}

export function useCreateSprint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateSprintRequest) => sprintService.create(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sprintKeys.lists() });
    },
  });
}

export function useUpdateSprint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: UpdateSprintRequest;
    }) => sprintService.update(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sprintKeys.lists() });
    },
  });
}

export function useDeleteSprint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => sprintService.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sprintKeys.lists() });
    },
  });
}
