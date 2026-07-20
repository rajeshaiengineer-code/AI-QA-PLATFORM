-- Sample QA pipeline data (test cases, BDD, Playwright, executions)
-- Depends on: database/seeds/001_sample_stories.sql
-- Safe to re-run: fixed UUIDs + ON CONFLICT DO NOTHING

BEGIN;

INSERT INTO test_cases (
  id, story_id, title, description, preconditions, steps, expected_result,
  priority, is_automated, order_index, category, source, status, tags,
  provider, model, created_at, updated_at, is_deleted, version
) VALUES
(
  'eeeeeeee-eeee-4eee-8eee-eeeeeeee0001',
  'dddddddd-dddd-4ddd-8ddd-dddddddd0001',
  'Reset password with valid token',
  'Happy-path password reset via emailed link.',
  'User has a valid reset token email',
  '[{"action":"Open reset link","expected":"Reset form loads"},{"action":"Enter new password and submit","expected":"Success message shown"}]'::json,
  'Password is updated and user can log in',
  'high', true, 0, 'positive', 'ai', 'approved', '["auth","smoke"]'::json,
  'seed', 'demo', now(), now(), false, 1
),
(
  'eeeeeeee-eeee-4eee-8eee-eeeeeeee0002',
  'dddddddd-dddd-4ddd-8ddd-dddddddd0001',
  'Reset password with expired token',
  'Negative path for expired reset tokens.',
  'User has an expired reset token',
  '[{"action":"Open expired reset link","expected":"Error page or message"},{"action":"Attempt submit","expected":"Request new link CTA shown"}]'::json,
  'User is blocked from resetting with expired token',
  'high', false, 1, 'negative', 'ai', 'pending_review', '["auth"]'::json,
  'seed', 'demo', now(), now(), false, 1
),
(
  'eeeeeeee-eeee-4eee-8eee-eeeeeeee0003',
  'dddddddd-dddd-4ddd-8ddd-dddddddd0002',
  'Checkout rejects invalid CVV',
  'Payment form validation for CVV.',
  'Cart has at least one item',
  '[{"action":"Enter card details with invalid CVV","expected":"Inline validation error"},{"action":"Submit payment","expected":"Payment not processed"}]'::json,
  'Clear CVV error is shown and charge is not created',
  'critical', true, 0, 'negative', 'manual', 'approved', '["payments"]'::json,
  NULL, NULL, now(), now(), false, 1
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO bdd_features (
  id, story_id, name, description, gherkin_content, tags, scenarios,
  source_test_case_ids, include_drafts, provider, model, summary,
  created_at, updated_at, is_deleted, version
) VALUES (
  'ffffffff-ffff-4fff-8fff-ffffffff0001',
  'dddddddd-dddd-4ddd-8ddd-dddddddd0001',
  'Password reset',
  'As a user I can reset my password',
  $gh$@auth
Feature: Password reset
  Scenario: Reset with valid token
    Given a valid reset token
    When the user submits a new password
    Then the password is updated
$gh$,
  '["@auth"]'::json,
  '[{"type":"scenario","name":"Reset with valid token","tags":["@positive"],"steps":[{"keyword":"Given","text":"a valid reset token"},{"keyword":"When","text":"the user submits a new password"},{"keyword":"Then","text":"the password is updated"}]}]'::json,
  '["eeeeeeee-eeee-4eee-8eee-eeeeeeee0001"]'::json,
  false, 'seed', 'demo', 'Demo BDD for password reset',
  now(), now(), false, 1
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO automation_artifacts (
  id, story_id, name, description, language, framework,
  page_objects, locators, fixtures, utilities, assertions, hooks, specs,
  source_bdd_feature_ids, source_test_case_ids, use_bdd, use_test_cases,
  include_drafts, provider, model, summary,
  created_at, updated_at, is_deleted, version
) VALUES (
  'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeee0001',
  'dddddddd-dddd-4ddd-8ddd-dddddddd0001',
  'password-reset',
  'Demo Playwright suite for password reset',
  'typescript', 'playwright',
  $json$[{"path":"pages/PasswordResetPage.ts","content":"export class PasswordResetPage { async open(url: string) { /* demo */ } }"}]$json$::json,
  $json$[{"path":"locators/passwordReset.ts","content":"export const passwordReset = { email: '#email' };"}]$json$::json,
  '[]'::json, '[]'::json, '[]'::json, '[]'::json,
  $json$[{"path":"tests/password-reset.spec.ts","content":"import { test, expect } from '@playwright/test'; test('reset password', async ({ page }) => { await expect(page).toBeDefined(); });"}]$json$::json,
  '["ffffffff-ffff-4fff-8fff-ffffffff0001"]'::json,
  '["eeeeeeee-eeee-4eee-8eee-eeeeeeee0001"]'::json,
  true, true, false, 'seed', 'demo', 'Seeded Playwright artifact',
  now(), now(), false, 1
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO automation_jobs (
  id, project_id, sprint_id, name, status,
  started_at, completed_at, config, error_message,
  created_at, updated_at, is_deleted, version
) VALUES (
  'bbbbbbbb-cccc-4ddd-8eee-ffffffff0001',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  'Demo stub run — Sprint 14',
  'completed',
  now() - interval '10 minutes',
  now() - interval '9 minutes',
  '{"runner":"stub","story_id":"dddddddd-dddd-4ddd-8ddd-dddddddd0001"}'::json,
  NULL,
  now(), now(), false, 1
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO executions (
  id, automation_job_id, test_case_id, status,
  started_at, completed_at, duration_ms, error_message, stack_trace,
  evidence_url, retry_count, created_at, updated_at, is_deleted, version
) VALUES
(
  'cccccccc-dddd-4eee-8fff-aaaaaaa00001',
  'bbbbbbbb-cccc-4ddd-8eee-ffffffff0001',
  'eeeeeeee-eeee-4eee-8eee-eeeeeeee0001',
  'passed',
  now() - interval '10 minutes',
  now() - interval '9 minutes 50 seconds',
  850, NULL, NULL, NULL, 0,
  now(), now(), false, 1
),
(
  'cccccccc-dddd-4eee-8fff-aaaaaaa00002',
  'bbbbbbbb-cccc-4ddd-8eee-ffffffff0001',
  'eeeeeeee-eeee-4eee-8eee-eeeeeeee0003',
  'failed',
  now() - interval '9 minutes 50 seconds',
  now() - interval '9 minutes 40 seconds',
  1200,
  'Expected validation error for invalid CVV but payment API returned 500',
  'Error: stub failure\n    at StubTestRunner.run',
  'stub://screenshots/cvv-fail.png',
  0,
  now(), now(), false, 1
)
ON CONFLICT (id) DO NOTHING;

COMMIT;
