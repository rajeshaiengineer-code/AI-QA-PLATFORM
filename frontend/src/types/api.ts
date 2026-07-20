/**
 * API Types — shapes returned by the FastAPI backend
 */

export interface ApiErrorBody {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface MessageResponse {
  success: boolean;
  message: string;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}
