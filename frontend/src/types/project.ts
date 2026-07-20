/**
 * Project Types — aligned with backend ProjectResponse / ProjectCreate
 */

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  key: string;
  description: string | null;
  external_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
  is_deleted: boolean;
  version: number;
}

export interface CreateProjectRequest {
  organization_id: string;
  name: string;
  key: string;
  description?: string | null;
  external_id?: string | null;
  is_active?: boolean;
}

export interface UpdateProjectRequest {
  organization_id?: string;
  name?: string;
  key?: string;
  description?: string | null;
  external_id?: string | null;
  is_active?: boolean;
}

export interface ProjectListParams {
  page?: number;
  page_size?: number;
  organization_id?: string;
  is_active?: boolean;
  search?: string;
}

export interface ProjectDashboardStats {
  project_id: string;
  story_total: number;
  story_by_status: Record<string, number>;
  sprint_total: number;
  active_sprint_total: number;
}
