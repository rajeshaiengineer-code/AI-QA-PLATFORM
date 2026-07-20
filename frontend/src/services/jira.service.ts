/**
 * Jira Connector Service
 */

import { apiClient } from "@/lib/axios";
import { API_ENDPOINTS } from "@/lib/constants";
import type {
  JiraBoard,
  JiraConnectRequest,
  JiraConnectResponse,
  JiraHealthResponse,
  JiraMessageResponse,
  JiraProject,
  JiraSprint,
  JiraSyncRequest,
  JiraSyncResponse,
} from "@/types/jira";

export const jiraService = {
  async connect(payload: JiraConnectRequest): Promise<JiraConnectResponse> {
    const { data } = await apiClient.post<JiraConnectResponse>(
      `${API_ENDPOINTS.JIRA}/connect`,
      payload
    );
    return data;
  },

  async disconnect(): Promise<JiraMessageResponse> {
    const { data } = await apiClient.post<JiraMessageResponse>(
      `${API_ENDPOINTS.JIRA}/disconnect`
    );
    return data;
  },

  async health(): Promise<JiraHealthResponse> {
    const { data } = await apiClient.get<JiraHealthResponse>(
      `${API_ENDPOINTS.JIRA}/health`
    );
    return data;
  },

  async listProjects(): Promise<JiraProject[]> {
    const { data } = await apiClient.get<JiraProject[]>(
      `${API_ENDPOINTS.JIRA}/projects`
    );
    return data;
  },

  async listBoards(projectKey?: string): Promise<JiraBoard[]> {
    const { data } = await apiClient.get<JiraBoard[]>(
      `${API_ENDPOINTS.JIRA}/boards`,
      { params: projectKey ? { project_key: projectKey } : undefined }
    );
    return data;
  },

  async listSprints(boardId: string): Promise<JiraSprint[]> {
    const { data } = await apiClient.get<JiraSprint[]>(
      `${API_ENDPOINTS.JIRA}/sprints`,
      { params: { board_id: boardId } }
    );
    return data;
  },

  async sync(payload: JiraSyncRequest): Promise<JiraSyncResponse> {
    const { data } = await apiClient.post<JiraSyncResponse>(
      `${API_ENDPOINTS.JIRA}/sync`,
      payload,
      { timeout: 120_000 }
    );
    return data;
  },
};
