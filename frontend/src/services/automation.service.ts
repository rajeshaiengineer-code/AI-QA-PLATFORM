/**
 * Automation Service — BDD, Playwright, executions, failure analysis
 */

import { apiClient } from "@/lib/axios";
import { API_ENDPOINTS } from "@/lib/constants";
import type { PaginatedResponse } from "@/types/api";
import type {
  AutomationArtifact,
  BddFeature,
  BddGenerateResponse,
  CreateJiraBugRequest,
  CreateJiraBugResponse,
  Execution,
  ExecutionRunRequest,
  ExecutionRunResponse,
  FailureAnalysis,
  PlaywrightGenerateResponse,
} from "@/types/automation";

export const automationService = {
  async generateBdd(
    storyId: string,
    includeDrafts = false
  ): Promise<BddGenerateResponse> {
    const { data } = await apiClient.post<BddGenerateResponse>(
      `${API_ENDPOINTS.STORIES}/${storyId}/bdd`,
      { include_drafts: includeDrafts },
      { timeout: 120_000 }
    );
    return data;
  },

  async listBdd(
    storyId: string,
    params: { page?: number; page_size?: number } = {}
  ): Promise<PaginatedResponse<BddFeature>> {
    const { data } = await apiClient.get<PaginatedResponse<BddFeature>>(
      `${API_ENDPOINTS.STORIES}/${storyId}/bdd`,
      { params }
    );
    return data;
  },

  async generatePlaywright(
    storyId: string,
    opts: { include_drafts?: boolean; use_bdd?: boolean; use_test_cases?: boolean } = {}
  ): Promise<PlaywrightGenerateResponse> {
    const { data } = await apiClient.post<PlaywrightGenerateResponse>(
      `${API_ENDPOINTS.STORIES}/${storyId}/playwright`,
      {
        use_bdd: opts.use_bdd ?? true,
        use_test_cases: opts.use_test_cases ?? true,
        include_drafts: opts.include_drafts ?? false,
      },
      { timeout: 120_000 }
    );
    return data;
  },

  async listPlaywright(
    storyId: string,
    params: { page?: number; page_size?: number } = {}
  ): Promise<PaginatedResponse<AutomationArtifact>> {
    const { data } = await apiClient.get<PaginatedResponse<AutomationArtifact>>(
      `${API_ENDPOINTS.STORIES}/${storyId}/playwright`,
      { params }
    );
    return data;
  },

  async run(payload: ExecutionRunRequest): Promise<ExecutionRunResponse> {
    const { data } = await apiClient.post<ExecutionRunResponse>(
      API_ENDPOINTS.EXECUTIONS_RUN,
      payload
    );
    return data;
  },

  async listExecutions(
    params: {
      page?: number;
      page_size?: number;
      automation_job_id?: string;
      test_case_id?: string;
      status?: string;
    } = {}
  ): Promise<PaginatedResponse<Execution>> {
    const { data } = await apiClient.get<PaginatedResponse<Execution>>(
      API_ENDPOINTS.EXECUTIONS,
      { params }
    );
    return data;
  },

  async getExecution(id: string): Promise<Execution> {
    const { data } = await apiClient.get<Execution>(
      `${API_ENDPOINTS.EXECUTIONS}/${id}`
    );
    return data;
  },

  async retryExecution(id: string): Promise<Execution> {
    const { data } = await apiClient.post<Execution>(
      `${API_ENDPOINTS.EXECUTIONS}/${id}/retry`
    );
    return data;
  },

  async analyzeFailure(executionId: string): Promise<FailureAnalysis> {
    const { data } = await apiClient.post<FailureAnalysis>(
      `${API_ENDPOINTS.EXECUTIONS}/${executionId}/analyze-failure`,
      {},
      { timeout: 120_000 }
    );
    return data;
  },

  async getFailureAnalysis(executionId: string): Promise<FailureAnalysis> {
    const { data } = await apiClient.get<FailureAnalysis>(
      `${API_ENDPOINTS.EXECUTIONS}/${executionId}/failure-analysis`
    );
    return data;
  },

  async createJiraBug(
    executionId: string,
    payload: CreateJiraBugRequest
  ): Promise<CreateJiraBugResponse> {
    const { data } = await apiClient.post<CreateJiraBugResponse>(
      `${API_ENDPOINTS.EXECUTIONS}/${executionId}/create-jira-bug`,
      payload
    );
    return data;
  },
};
