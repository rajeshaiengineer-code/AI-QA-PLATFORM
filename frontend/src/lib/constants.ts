/**
 * Application Constants
 * Centralized constants for the application
 */

export const APP_NAME = 'AI QA Platform';
export const APP_VERSION = '1.0.0';

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  PROJECTS: '/projects',
  SPRINTS: '/sprints',
  STORIES: '/stories',
  TEST_CASES: '/test-cases',
  AUTOMATION: '/automation',
  REPORTS: '/reports',
  SETTINGS: '/integrations',
} as const;

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
  },
  DASHBOARD: '/dashboard',
  PROJECTS: '/projects',
  SPRINTS: '/sprints',
  STORIES: '/stories',
  TEST_CASES: '/test-cases',
  EXECUTIONS: '/executions',
  EXECUTIONS_RUN: '/executions/run',
  JIRA: '/connectors/jira',
  BDD: '/bdd',
  PLAYWRIGHT: '/playwright',
} as const;

/** Demo seed org (database/seeds/001_sample_stories.sql) */
export const DEFAULT_ORG_ID =
  process.env.NEXT_PUBLIC_DEFAULT_ORG_ID?.trim() ||
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';

export const DEFAULT_PROJECT_ID =
  process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID?.trim() ||
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';

export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 10,
  PAGE_SIZE_OPTIONS: [10, 25, 50, 100],
} as const;
