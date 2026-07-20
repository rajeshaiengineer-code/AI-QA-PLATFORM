/**
 * Authentication Types
 * Types for authentication and user management
 */

export type OrgRole = "admin" | "qa" | "engineer" | "viewer";

export interface User {
  id: string;
  email: string;
  name: string;
  role: OrgRole | string;
  avatar?: string;
  createdAt: string;
  updatedAt: string;
}

export enum UserRole {
  ADMIN = "admin",
  QA = "qa",
  ENGINEER = "engineer",
  VIEWER = "viewer",
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  accessToken: string;
  refreshToken: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}
