/**
 * Story Types — aligned with backend StoryResponse / StoryCreate / StoryUpdate
 */

export type StoryStatus =
  | "draft"
  | "ready"
  | "in_progress"
  | "in_review"
  | "done"
  | "blocked";

export type StoryType =
  | "feature"
  | "bug"
  | "task"
  | "spike"
  | "enhancement";

export type Priority = "critical" | "high" | "medium" | "low";

export interface Story {
  id: string;
  project_id: string;
  sprint_id: string | null;
  title: string;
  description: string | null;
  status: StoryStatus;
  story_type: StoryType;
  priority: Priority;
  story_points: number | null;
  external_id: string | null;
  jira_issue_id: string | null;
  labels: string[] | null;
  assignee: string | null;
  reporter: string | null;
  external_updated_at: string | null;
  rank: number | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
  is_deleted: boolean;
  version: number;
}

export interface CreateStoryRequest {
  project_id: string;
  title: string;
  description?: string | null;
  status?: StoryStatus;
  story_type?: StoryType;
  priority?: Priority;
  story_points?: number | null;
  external_id?: string | null;
  rank?: number | null;
  sprint_id?: string | null;
}

export interface UpdateStoryRequest {
  project_id?: string;
  title?: string;
  description?: string | null;
  status?: StoryStatus;
  story_type?: StoryType;
  priority?: Priority;
  story_points?: number | null;
  external_id?: string | null;
  rank?: number | null;
  sprint_id?: string | null;
}

export interface StoryListParams {
  page?: number;
  page_size?: number;
  status?: StoryStatus;
  story_type?: StoryType;
  priority?: Priority;
  sprint_id?: string;
  project_id?: string;
  search?: string;
}

export const STORY_STATUS_OPTIONS: { value: StoryStatus; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "ready", label: "Ready" },
  { value: "in_progress", label: "In Progress" },
  { value: "in_review", label: "In Review" },
  { value: "done", label: "Done" },
  { value: "blocked", label: "Blocked" },
];

export const STORY_TYPE_OPTIONS: { value: StoryType; label: string }[] = [
  { value: "feature", label: "Feature" },
  { value: "bug", label: "Bug" },
  { value: "task", label: "Task" },
  { value: "spike", label: "Spike" },
  { value: "enhancement", label: "Enhancement" },
];

export const PRIORITY_OPTIONS: { value: Priority; label: string }[] = [
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];
