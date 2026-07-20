/**
 * Story Service — Axios client for Story CRUD APIs
 */

import { apiClient } from "@/lib/axios";
import { API_ENDPOINTS } from "@/lib/constants";
import type { MessageResponse, PaginatedResponse } from "@/types/api";
import type {
  CreateStoryRequest,
  Story,
  StoryListParams,
  UpdateStoryRequest,
} from "@/types/story";

function cleanParams(params: StoryListParams): Record<string, string | number> {
  const result: Record<string, string | number> = {};
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      result[key] = value as string | number;
    }
  });
  return result;
}

export const storyService = {
  async list(params: StoryListParams = {}): Promise<PaginatedResponse<Story>> {
    const { data } = await apiClient.get<PaginatedResponse<Story>>(
      API_ENDPOINTS.STORIES,
      { params: cleanParams(params) }
    );
    return data;
  },

  async getById(id: string): Promise<Story> {
    const { data } = await apiClient.get<Story>(`${API_ENDPOINTS.STORIES}/${id}`);
    return data;
  },

  async create(payload: CreateStoryRequest): Promise<Story> {
    const { data } = await apiClient.post<Story>(API_ENDPOINTS.STORIES, payload);
    return data;
  },

  async update(id: string, payload: UpdateStoryRequest): Promise<Story> {
    const { data } = await apiClient.put<Story>(
      `${API_ENDPOINTS.STORIES}/${id}`,
      payload
    );
    return data;
  },

  async remove(id: string): Promise<MessageResponse> {
    const { data } = await apiClient.delete<MessageResponse>(
      `${API_ENDPOINTS.STORIES}/${id}`
    );
    return data;
  },
};
