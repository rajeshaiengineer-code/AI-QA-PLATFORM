-- Sample seed data for AI QA Platform (local testing)
-- Safe to re-run: uses fixed UUIDs and ON CONFLICT / upserts where possible.

BEGIN;

-- Demo organization
INSERT INTO organizations (
  id, name, slug, description, is_active,
  created_at, updated_at, is_deleted, version
) VALUES (
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'Acme QA Labs',
  'acme-qa-labs',
  'Demo organization for local Story Management testing',
  true,
  now(), now(), false, 1
)
ON CONFLICT (id) DO NOTHING;

-- Demo project
INSERT INTO projects (
  id, organization_id, name, key, description, is_active,
  created_at, updated_at, is_deleted, version
) VALUES (
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'Payments Portal',
  'PAY',
  'Demo project used by Story Management UI',
  true,
  now(), now(), false, 1
)
ON CONFLICT (id) DO NOTHING;

-- Demo sprint
INSERT INTO sprints (
  id, project_id, name, goal, start_date, end_date, is_active,
  created_at, updated_at, is_deleted, version
) VALUES (
  'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'Sprint 14',
  'Ship checkout reliability improvements',
  CURRENT_DATE - 7,
  CURRENT_DATE + 7,
  true,
  now(), now(), false, 1
)
ON CONFLICT (id) DO NOTHING;

-- Sample stories (mixed status/type/priority for filter testing)
INSERT INTO stories (
  id, project_id, sprint_id, title, description,
  status, story_type, priority, story_points, external_id, rank,
  created_at, updated_at, is_deleted, version
) VALUES
(
  'dddddddd-dddd-4ddd-8ddd-dddddddd0001',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  'User can reset password via email',
  'As a registered user I want to reset my password so I can regain access.',
  'ready', 'feature', 'high', 5, 'PAY-101', 1,
  now(), now(), false, 1
),
(
  'dddddddd-dddd-4ddd-8ddd-dddddddd0002',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  'Checkout fails on invalid CVV',
  'Payment form should show a clear error when CVV is invalid.',
  'in_progress', 'bug', 'critical', 3, 'PAY-102', 2,
  now(), now(), false, 1
),
(
  'dddddddd-dddd-4ddd-8ddd-dddddddd0003',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  'Add saved payment methods',
  'Allow users to save and reuse cards for faster checkout.',
  'done', 'feature', 'critical', 8, 'PAY-103', 3,
  now(), now(), false, 1
),
(
  'dddddddd-dddd-4ddd-8ddd-dddddddd0004',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  NULL,
  'Spike: evaluate 3DS2 providers',
  'Research Strong Customer Authentication options for EU traffic.',
  'draft', 'spike', 'medium', 2, 'PAY-104', 4,
  now(), now(), false, 1
),
(
  'dddddddd-dddd-4ddd-8ddd-dddddddd0005',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  'Refund webhook retry handling',
  'Retries and idempotency for refund confirmation webhooks.',
  'in_review', 'enhancement', 'high', 5, 'PAY-105', 5,
  now(), now(), false, 1
),
(
  'dddddddd-dddd-4ddd-8ddd-dddddddd0006',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  NULL,
  'Document merchant onboarding checklist',
  'Internal task to capture ops checklist for new merchants.',
  'blocked', 'task', 'low', 1, 'PAY-106', 6,
  now(), now(), false, 1
)
ON CONFLICT (id) DO NOTHING;

COMMIT;

-- Helpful IDs for the UI
SELECT 'Project ID (use in Create Story)' AS label, id::text AS value
FROM projects WHERE key = 'PAY'
UNION ALL
SELECT 'Sprint ID (optional filter)', id::text
FROM sprints WHERE name = 'Sprint 14'
UNION ALL
SELECT 'Story count', COUNT(*)::text
FROM stories WHERE is_deleted = false;
