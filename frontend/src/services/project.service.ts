/**
 * Project Service — Axios client for Project CRUD APIs
 */

import { apiClient } from "@/lib/axios";
import { API_ENDPOINTS } from "@/lib/constants";
import type { MessageResponse, PaginatedResponse } from "@/types/api";
import type {
  CreateProjectRequest,
  Project,
  ProjectDashboardStats,
  ProjectListParams,
  UpdateProjectRequest,
} from "@/types/project";

function cleanParams(
  params: ProjectListParams
): Record<string, string | number | boolean> {
  const result: Record<string, string | number | boolean> = {};
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      result[key] = value as string | number | boolean;
    }
  });
  return result;
}

export const projectService = {
  async list(
    params: ProjectListParams = {}
  ): Promise<PaginatedResponse<Project>> {
    const { data } = await apiClient.get<PaginatedResponse<Project>>(
      API_ENDPOINTS.PROJECTS,
      { params: cleanParams(params) }
    );
    return data;
  },

  async getById(id: string): Promise<Project> {
    const { data } = await apiClient.get<Project>(
      `${API_ENDPOINTS.PROJECTS}/${id}`
    );
    return data;
  },

  async getDashboard(id: string): Promise<ProjectDashboardStats> {
    const { data } = await apiClient.get<ProjectDashboardStats>(
      `${API_ENDPOINTS.PROJECTS}/${id}/dashboard`
    );
    return data;
  },

  async create(payload: CreateProjectRequest): Promise<Project> {
    const { data } = await apiClient.post<Project>(
      API_ENDPOINTS.PROJECTS,
      payload
    );
    return data;
  },

  async update(id: string, payload: UpdateProjectRequest): Promise<Project> {
    const { data } = await apiClient.put<Project>(
      `${API_ENDPOINTS.PROJECTS}/${id}`,
      payload
    );
    return data;
  },

  async remove(id: string): Promise<MessageResponse> {
    const { data } = await apiClient.delete<MessageResponse>(
      `${API_ENDPOINTS.PROJECTS}/${id}`
    );
    return data;
  },
};
