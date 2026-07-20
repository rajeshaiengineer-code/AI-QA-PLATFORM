/**
 * Jira connector hooks
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { jiraService } from "@/services/jira.service";
import type { JiraConnectRequest, JiraSyncRequest } from "@/types/jira";

export const jiraKeys = {
  all: ["jira"] as const,
  health: () => [...jiraKeys.all, "health"] as const,
  projects: () => [...jiraKeys.all, "projects"] as const,
  boards: (projectKey?: string) =>
    [...jiraKeys.all, "boards", projectKey ?? "all"] as const,
};

export function useJiraHealth(enabled = false) {
  return useQuery({
    queryKey: jiraKeys.health(),
    queryFn: () => jiraService.health(),
    enabled,
    retry: false,
  });
}

export function useConnectJira() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: JiraConnectRequest) => jiraService.connect(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: jiraKeys.all });
    },
  });
}

export function useDisconnectJira() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => jiraService.disconnect(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: jiraKeys.all });
    },
  });
}

export function useSyncJira() {
  return useMutation({
    mutationFn: (payload: JiraSyncRequest) => jiraService.sync(payload),
  });
}

export function useJiraProjects(enabled = false) {
  return useQuery({
    queryKey: jiraKeys.projects(),
    queryFn: () => jiraService.listProjects(),
    enabled,
    retry: false,
  });
}
