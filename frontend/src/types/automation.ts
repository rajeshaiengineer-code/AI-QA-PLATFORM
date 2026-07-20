/**
 * Automation + Execution types — aligned with backend schemas
 */

export type ExecutionStatus =
  | "pending"
  | "running"
  | "passed"
  | "failed"
  | "skipped"
  | "error"
  | "blocked";

export type AutomationStatus =
  | "pending"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface BddFeature {
  id: string;
  story_id: string;
  name: string;
  description: string | null;
  gherkin_content: string;
  tags: string[] | null;
  scenarios: unknown[] | null;
  source_test_case_ids: string[] | null;
  include_drafts: boolean;
  provider: string | null;
  model: string | null;
  summary: string | null;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
  version: number;
}

export interface BddGenerateResponse {
  story_id: string;
  feature: BddFeature;
  summary?: string | null;
  provider?: string | null;
  model?: string | null;
  source_test_case_count?: number;
}

export interface AutomationFile {
  path: string;
  content: string;
  description?: string | null;
  kind?: string | null;
}

export interface AutomationArtifact {
  id: string;
  story_id: string;
  name: string;
  description: string | null;
  language: string;
  framework: string;
  page_objects: AutomationFile[] | null;
  locators: AutomationFile[] | null;
  fixtures: AutomationFile[] | null;
  utilities: AutomationFile[] | null;
  assertions: AutomationFile[] | null;
  hooks: AutomationFile[] | null;
  specs: AutomationFile[] | null;
  source_bdd_feature_ids: string[] | null;
  source_test_case_ids: string[] | null;
  use_bdd: boolean;
  use_test_cases: boolean;
  include_drafts: boolean;
  provider: string | null;
  model: string | null;
  summary: string | null;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
  version: number;
}

export interface PlaywrightGenerateResponse {
  story_id: string;
  artifact: AutomationArtifact;
  summary?: string | null;
  provider?: string | null;
  model?: string | null;
  source_bdd_feature_count?: number;
  source_test_case_count?: number;
  file_count?: number;
}

export interface Execution {
  id: string;
  automation_job_id: string;
  test_case_id: string;
  status: ExecutionStatus;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
  stack_trace: string | null;
  evidence_url: string | null;
  retry_count: number;
  created_at: string;
  updated_at: string;
  version: number;
  automation_job?: AutomationJobSummary | null;
}

export interface AutomationJobSummary {
  id: string;
  project_id: string;
  sprint_id: string | null;
  name: string;
  status: AutomationStatus;
  triggered_by: string | null;
  started_at: string | null;
  completed_at: string | null;
  config: Record<string, unknown> | null;
  error_message: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AutomationJob extends AutomationJobSummary {
  executions: Execution[];
  passed: number;
  failed: number;
  error: number;
  skipped: number;
  total: number;
}

export interface ExecutionRunRequest {
  story_id?: string;
  automation_artifact_id?: string;
  automation_job_id?: string;
  include_drafts?: boolean;
  force_fail_test_case_ids?: string[];
  runner?: "stub" | "playwright";
  name?: string;
  config?: Record<string, unknown>;
}

export interface ExecutionRunResponse {
  job: AutomationJob;
  workflow_run_id?: string | null;
  runner: string;
}

export interface FailureAnalysis {
  id: string;
  execution_id: string;
  category: string;
  is_flaky: boolean;
  is_product_bug: boolean;
  summary: string;
  root_cause: string;
  suggested_fix: string;
  confidence: number | null;
  notes: string | null;
  logs: string | null;
  screenshot_url: string | null;
  provider: string | null;
  model: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateJiraBugRequest {
  jira_project_key: string;
  failure_analysis_id?: string;
  title?: string;
  description?: string;
  priority?: string;
  issue_type?: string;
  labels?: string[];
}

export interface CreateJiraBugResponse {
  bug: {
    id: string;
    title: string;
    external_id: string | null;
    status: string;
    priority: string;
    extra_metadata?: Record<string, unknown> | null;
  };
  jira_key: string;
  jira_id?: string | null;
  jira_url?: string | null;
}
