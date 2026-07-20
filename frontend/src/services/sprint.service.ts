/**
 * Sprint Service — Axios client for Sprint CRUD APIs
 */

import { apiClient } from "@/lib/axios";
import type { MessageResponse, PaginatedResponse } from "@/types/api";
import type {
  CreateSprintRequest,
  Sprint,
  SprintListParams,
  UpdateSprintRequest,
} from "@/types/sprint";

const SPRINTS = "/sprints";

function cleanParams(
  params: SprintListParams
): Record<string, string | number | boolean> {
  const result: Record<string, string | number | boolean> = {};
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      result[key] = value as string | number | boolean;
    }
  });
  return result;
}

export const sprintService = {
  async list(params: SprintListParams = {}): Promise<PaginatedResponse<Sprint>> {
    const { data } = await apiClient.get<PaginatedResponse<Sprint>>(SPRINTS, {
      params: cleanParams(params),
    });
    return data;
  },

  async getById(id: string): Promise<Sprint> {
    const { data } = await apiClient.get<Sprint>(`${SPRINTS}/${id}`);
    return data;
  },

  async create(payload: CreateSprintRequest): Promise<Sprint> {
    const { data } = await apiClient.post<Sprint>(SPRINTS, payload);
    return data;
  },

  async update(id: string, payload: UpdateSprintRequest): Promise<Sprint> {
    const { data } = await apiClient.put<Sprint>(`${SPRINTS}/${id}`, payload);
    return data;
  },

  async remove(id: string): Promise<MessageResponse> {
    const { data } = await apiClient.delete<MessageResponse>(`${SPRINTS}/${id}`);
    return data;
  },
};
