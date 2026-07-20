/**
 * Test Case Types — aligned with backend TestCaseResponse
 */

export type TestCaseStatus =
  | "draft"
  | "pending_review"
  | "approved"
  | "rejected";

export type TestCaseCategory =
  | "positive"
  | "negative"
  | "boundary"
  | "api"
  | "security"
  | "database"
  | "accessibility"
  | "performance";

export type TestCaseSource = "ai" | "manual" | "imported";

export type TestCasePriority = "critical" | "high" | "medium" | "low";

export interface TestStep {
  action: string;
  expected?: string | null;
}

export interface TestCase {
  id: string;
  story_id: string;
  acceptance_criteria_id: string | null;
  title: string;
  description: string | null;
  preconditions: string | null;
  steps: TestStep[] | null;
  expected_result: string | null;
  priority: TestCasePriority;
  is_automated: boolean;
  order_index: number;
  category: TestCaseCategory | null;
  source: TestCaseSource;
  status: TestCaseStatus;
  rejection_reason: string | null;
  tags: string[] | null;
  provider: string | null;
  model: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
  is_deleted: boolean;
  version: number;
}

export interface TestCaseUpdateRequest {
  title?: string;
  description?: string | null;
  preconditions?: string | null;
  steps?: TestStep[];
  expected_result?: string | null;
  priority?: TestCasePriority;
  is_automated?: boolean;
  category?: TestCaseCategory | null;
  tags?: string[];
  change_reason?: string;
}

export interface TestCaseGenerateRequest {
  logical_model?: string;
  categories?: TestCaseCategory[];
}

export interface TestCaseGenerateResponse {
  story_id: string;
  count: number;
  items: TestCase[];
  summary?: string | null;
  provider?: string | null;
  model?: string | null;
}

export interface TestCaseDecisionResponse {
  test_case: TestCase;
  workflow_advanced: boolean;
  workflow_run_id?: string | null;
  message?: string | null;
}

export interface TestCaseApproveAllResponse {
  story_id: string;
  approved_count: number;
  items: TestCase[];
  workflow_advanced: boolean;
  workflow_run_id?: string | null;
  message?: string | null;
}

export interface StoryAnalysis {
  id: string;
  story_id: string;
  summary?: string | null;
  complexity?: string | null;
  risks?: unknown;
  suggested_test_areas?: unknown;
  ambiguities?: unknown;
  provider?: string | null;
  model?: string | null;
  created_at: string;
  updated_at: string;
}

export const TEST_CASE_STATUS_OPTIONS: {
  value: TestCaseStatus;
  label: string;
}[] = [
  { value: "draft", label: "Draft" },
  { value: "pending_review", label: "Pending review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];
