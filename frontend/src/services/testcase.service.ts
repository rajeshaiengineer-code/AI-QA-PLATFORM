/**
 * Test Case Service — QA review + generation APIs
 */

import { apiClient } from "@/lib/axios";
import { API_ENDPOINTS } from "@/lib/constants";
import type { PaginatedResponse } from "@/types/api";
import type {
  TestCase,
  TestCaseApproveAllResponse,
  TestCaseDecisionResponse,
  TestCaseGenerateRequest,
  TestCaseGenerateResponse,
  TestCaseUpdateRequest,
  StoryAnalysis,
} from "@/types/testcase";

export const testCaseService = {
  async listByStory(
    storyId: string,
    params: {
      page?: number;
      page_size?: number;
      category?: string;
      source?: string;
    } = {}
  ): Promise<PaginatedResponse<TestCase>> {
    const { data } = await apiClient.get<PaginatedResponse<TestCase>>(
      `${API_ENDPOINTS.STORIES}/${storyId}/test-cases`,
      { params }
    );
    return data;
  },

  async getById(id: string): Promise<TestCase> {
    const { data } = await apiClient.get<TestCase>(
      `${API_ENDPOINTS.TEST_CASES}/${id}`
    );
    return data;
  },

  async update(id: string, payload: TestCaseUpdateRequest): Promise<TestCase> {
    const { data } = await apiClient.put<TestCase>(
      `${API_ENDPOINTS.TEST_CASES}/${id}`,
      payload
    );
    return data;
  },

  async approve(id: string, note?: string): Promise<TestCaseDecisionResponse> {
    const { data } = await apiClient.post<TestCaseDecisionResponse>(
      `${API_ENDPOINTS.TEST_CASES}/${id}/approve`,
      note ? { note } : {}
    );
    return data;
  },

  async reject(
    id: string,
    reason?: string
  ): Promise<TestCaseDecisionResponse> {
    const { data } = await apiClient.post<TestCaseDecisionResponse>(
      `${API_ENDPOINTS.TEST_CASES}/${id}/reject`,
      reason ? { reason } : {}
    );
    return data;
  },

  async approveAll(storyId: string): Promise<TestCaseApproveAllResponse> {
    const { data } = await apiClient.post<TestCaseApproveAllResponse>(
      `${API_ENDPOINTS.STORIES}/${storyId}/test-cases/approve-all`
    );
    return data;
  },

  async generate(
    storyId: string,
    payload: TestCaseGenerateRequest = {}
  ): Promise<TestCaseGenerateResponse> {
    const { data } = await apiClient.post<TestCaseGenerateResponse>(
      `${API_ENDPOINTS.STORIES}/${storyId}/test-cases/generate`,
      payload,
      { timeout: 120_000 }
    );
    return data;
  },

  async analyzeStory(storyId: string): Promise<StoryAnalysis> {
    const { data } = await apiClient.post<StoryAnalysis>(
      `${API_ENDPOINTS.STORIES}/${storyId}/analyze`,
      {},
      { timeout: 120_000 }
    );
    return data;
  },

  async getStoryAnalysis(storyId: string): Promise<StoryAnalysis> {
    const { data } = await apiClient.get<StoryAnalysis>(
      `${API_ENDPOINTS.STORIES}/${storyId}/analyze`
    );
    return data;
  },
};
