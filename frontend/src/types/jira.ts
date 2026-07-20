/**
 * Jira Integration Types — aligned with backend schemas
 */

export interface JiraConnectRequest {
  base_url: string;
  email: string;
  api_token: string;
  acceptance_criteria_field?: string;
}

export interface JiraConnectResponse {
  connected: boolean;
  message: string;
  account_display_name?: string | null;
  base_url?: string | null;
}

export interface JiraHealthResponse {
  status: string;
  version?: string | null;
  latency_ms?: number | null;
  last_checked: string;
  message?: string | null;
  details?: Record<string, unknown>;
}

export interface JiraProject {
  id: string;
  key: string;
  name: string;
  style?: string | null;
  project_type_key?: string | null;
}

export interface JiraBoard {
  id: string;
  name: string;
  type?: string | null;
  project_key?: string | null;
}

export interface JiraSprint {
  id: string;
  name: string;
  state?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  goal?: string | null;
}

export interface JiraSyncRequest {
  organization_id: string;
  project_keys?: string[];
  board_id?: string;
  /** Default true — only import the active sprint */
  active_sprint_only?: boolean;
}

export interface JiraSyncResponse {
  id: string;
  connector_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  projects_synced: number;
  sprints_synced: number;
  stories_created: number;
  stories_updated: number;
  stories_skipped: number;
  error_message: string | null;
  details?: Record<string, unknown> | null;
}

export interface JiraMessageResponse {
  success: boolean;
  message: string;
}
