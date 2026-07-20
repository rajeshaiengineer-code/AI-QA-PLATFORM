/**
 * Dashboard reporting types
 */

export interface DashboardScope {
  organization_id: string | null;
  project_id: string | null;
}

export interface DashboardSummary {
  scope: DashboardScope;
  project_count: number;
  sprint_count: number;
  story_count: number;
  test_case_count: number;
  execution_count: number;
  automation_job_count: number;
  executions_by_status: Record<string, number>;
  stories_by_status: Record<string, number>;
}

export interface ExecutionTrendBucket {
  bucket_start: string;
  bucket_label: string;
  total: number;
  passed: number;
  failed: number;
  error: number;
  skipped: number;
  other: number;
}

export interface ExecutionTrends {
  scope: DashboardScope;
  days: number;
  bucket: string;
  from_date: string;
  to_date: string;
  buckets: ExecutionTrendBucket[];
}

export interface CoverageStats {
  scope: DashboardScope;
  stories_total: number;
  stories_with_test_cases: number;
  stories_without_test_cases: number;
  test_cases_total: number;
  test_cases_approved: number;
  test_cases_pending_review: number;
  test_cases_draft: number;
  test_cases_rejected: number;
  approved_ratio: number;
  coverage_ratio: number;
}

export interface AiMetrics {
  scope: DashboardScope;
  analyses_count: number;
  generated_test_cases: number;
  bdd_artifacts: number;
  playwright_artifacts: number;
}

export interface DashboardQueryParams {
  organization_id?: string;
  project_id?: string;
  days?: number;
  bucket?: "day" | "week";
}
