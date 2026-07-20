/**
 * Sprint Types — aligned with backend SprintResponse / SprintCreate
 */

export interface Sprint {
  id: string;
  project_id: string;
  name: string;
  goal: string | null;
  external_id: string | null;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
  is_deleted: boolean;
  version: number;
}

export interface CreateSprintRequest {
  project_id: string;
  name: string;
  goal?: string | null;
  external_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active?: boolean;
}

export interface UpdateSprintRequest {
  project_id?: string;
  name?: string;
  goal?: string | null;
  external_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active?: boolean;
}

export interface SprintListParams {
  page?: number;
  page_size?: number;
  project_id?: string;
  is_active?: boolean;
  search?: string;
}
