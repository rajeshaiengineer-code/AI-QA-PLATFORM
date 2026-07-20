/**
 * Project hooks — TanStack Query wrappers around projectService
 */

"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { getErrorMessage } from "@/hooks/useStories";
import { projectService } from "@/services/project.service";
import type { ProjectFilters } from "@/store/project.store";
import type {
  CreateProjectRequest,
  UpdateProjectRequest,
} from "@/types/project";

export { getErrorMessage };

export const projectKeys = {
  all: ["projects"] as const,
  lists: () => [...projectKeys.all, "list"] as const,
  list: (filters: ProjectFilters) => [...projectKeys.lists(), filters] as const,
  details: () => [...projectKeys.all, "detail"] as const,
  detail: (id: string) => [...projectKeys.details(), id] as const,
  dashboard: (id: string) => [...projectKeys.all, "dashboard", id] as const,
};

export function useProjectsQuery(filters: ProjectFilters) {
  return useQuery({
    queryKey: projectKeys.list(filters),
    queryFn: () =>
      projectService.list({
        page: filters.page,
        page_size: filters.page_size,
        organization_id: filters.organization_id || undefined,
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

export function useProjectQuery(id: string | null) {
  return useQuery({
    queryKey: projectKeys.detail(id ?? ""),
    queryFn: () => projectService.getById(id!),
    enabled: Boolean(id),
  });
}

export function useProjectDashboardQuery(id: string | null) {
  return useQuery({
    queryKey: projectKeys.dashboard(id ?? ""),
    queryFn: () => projectService.getDashboard(id!),
    enabled: Boolean(id),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateProjectRequest) =>
      projectService.create(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: UpdateProjectRequest;
    }) => projectService.update(id, payload),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
      void queryClient.invalidateQueries({
        queryKey: projectKeys.detail(variables.id),
      });
      void queryClient.invalidateQueries({
        queryKey: projectKeys.dashboard(variables.id),
      });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => projectService.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
}
