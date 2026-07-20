# API Documentation

## Document Information

| Field | Value |
|-------|-------|
| Base URL | `/api/v1` |
| Version | 1.6 |
| Last Updated | 2026-07-16 |
| Interactive docs | `/docs` (Swagger UI), `/redoc` (ReDoc), `/openapi.json` |

---

## 1. Overview

REST API for the AI QA Platform. JWT authentication is available under `/api/v1/auth`. By default `AUTH_ENABLED=false` so CRUD routes remain open for local development and tests; set `AUTH_ENABLED=true` to require Bearer tokens on protected write routes.

---

## 2. Authentication

See [`Authentication.md`](./Authentication.md) for full details.

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/auth/register` | Create user (+ optional org) |
| POST | `/api/v1/auth/login` | Email / password → JWT pair |
| POST | `/api/v1/auth/refresh` | Refresh token → new pair |
| GET | `/api/v1/auth/me` | Current user (Bearer required) |

Header when auth is enabled: `Authorization: Bearer <access_token>`.

Roles: `admin`, `qa`, `engineer`, `viewer`.

---

## 3. Common Headers

| Header | Description | Required |
|--------|-------------|----------|
| Content-Type | `application/json` | Yes (POST/PUT) |
| Accept | `application/json` | No |

---

## 4. Response Format

### 4.1 Success (resource)

Story create/get/update return the resource body directly (see StoryResponse).

### 4.2 Success (paginated list)

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 10,
  "total_pages": 0
}
```

### 4.3 Success (message)

```json
{
  "success": true,
  "message": "Story deleted successfully"
}
```

### 4.4 Error Response

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Story with id '...' not found",
    "details": {}
  }
}
```

---

## 5. Endpoints

### 5.1 Authentication

Tag: **Authentication**. Implemented — see [`Authentication.md`](./Authentication.md).

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register user; optional org create/join |
| POST | `/auth/login` | Login |
| POST | `/auth/refresh` | Refresh tokens |
| GET | `/auth/me` | Current user profile |

### 5.2 Projects

Not implemented (stories require an existing `project_id` in the database).

### 5.3 Stories

Tag: **Stories** (visible in Swagger UI under `/docs`).

Story key in search maps to `external_id` (e.g. Jira key). Soft delete is used for DELETE.

#### Enums

| Field | Values |
|-------|--------|
| status | `draft`, `ready`, `in_progress`, `in_review`, `done`, `blocked` |
| story_type | `feature`, `bug`, `task`, `spike`, `enhancement` |
| priority | `critical`, `high`, `medium`, `low` |

---

#### `GET /api/v1/stories`

List stories with pagination, filters, and search.

**Query parameters**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | int | 1 | Page number (≥ 1) |
| page_size | int | 10 | Page size (1–100) |
| status | enum | — | Filter by status |
| story_type | enum | — | Filter by type |
| priority | enum | — | Filter by priority |
| sprint_id | UUID | — | Filter by sprint |
| project_id | UUID | — | Filter by project |
| search | string | — | Case-insensitive match on `title` or `external_id` (story key) |

**Responses**

| Status | Body |
|--------|------|
| 200 | `StoryListResponse` |
| 422 | Validation error |

---

#### `GET /api/v1/stories/{story_id}`

Get a single story by UUID.

**Responses**

| Status | Body |
|--------|------|
| 200 | `StoryResponse` |
| 404 | Story not found |
| 422 | Invalid UUID |

---

#### `POST /api/v1/stories`

Create a story.

**Request body (`StoryCreate`)**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| project_id | UUID | Yes | Must reference an existing project |
| title | string | Yes | 1–500 chars |
| description | string | No | |
| status | enum | No | Default `draft` |
| story_type | enum | No | Default `feature` |
| priority | enum | No | Default `medium` |
| story_points | int | No | 0–100 |
| external_id | string | No | Story key (max 100) |
| rank | int | No | |
| sprint_id | UUID | No | Must belong to the same project |

**Example**

```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "User can reset password",
  "description": "As a user I want to reset my password via email.",
  "status": "draft",
  "story_type": "feature",
  "priority": "medium",
  "story_points": 3,
  "external_id": "PROJ-123",
  "rank": 1,
  "sprint_id": null
}
```

**Responses**

| Status | Body |
|--------|------|
| 201 | `StoryResponse` |
| 400 | Invalid project or sprint |
| 422 | Validation error |

---

#### `PUT /api/v1/stories/{story_id}`

Update a story. Only fields present in the body are updated.

**Request body (`StoryUpdate`)** — all fields optional; same types as create (including optional `project_id`).

**Responses**

| Status | Body |
|--------|------|
| 200 | `StoryResponse` |
| 400 | Invalid project or sprint |
| 404 | Story not found |
| 422 | Validation error |

---

#### `DELETE /api/v1/stories/{story_id}`

Soft-delete a story (`is_deleted = true`). Deleted stories are excluded from list/get.

**Responses**

| Status | Body |
|--------|------|
| 200 | `{ "success": true, "message": "Story deleted successfully" }` |
| 404 | Story not found |

---

#### `POST /api/v1/stories/{story_id}/analyze`

Run the AI Story Analyzer and persist results. Tags: **Stories**, **AI**.

Optional body:

```json
{ "logical_model": "default" }
```

**Responses**

| Status | Body |
|--------|------|
| 201 | `StoryAnalysisResponse` |
| 400 | AI / parse failure |
| 404 | Story not found |

#### `GET /api/v1/stories/{story_id}/analysis`

Latest analysis for the story.

| Status | Body |
|--------|------|
| 200 | `StoryAnalysisResponse` |
| 404 | Story or analysis not found |

See [`docs/StoryAnalyzer.md`](./StoryAnalyzer.md).

---

#### `POST /api/v1/stories/{story_id}/test-cases/generate`

Run the AI Test Case Generator and persist `TestCase` rows. Tags: **Stories**, **AI**, **Test Cases**.

Optional body:

```json
{
  "logical_model": "default",
  "categories": ["positive", "negative", "security"]
}
```

Categories (default: all): `positive`, `negative`, `boundary`, `api`, `security`, `database`, `accessibility`, `performance`.

**Responses**

| Status | Body |
|--------|------|
| 201 | `TestCaseGenerateResponse` (`count`, `items`, `summary`, `provider`, `model`) |
| 400 | AI / parse failure |
| 404 | Story not found |

#### `GET /api/v1/stories/{story_id}/test-cases`

Paginated test cases for the story. Query: `page`, `page_size`, optional `category`, `source` (`ai` \| `manual` \| `imported`), optional `status` (`draft` \| `pending_review` \| `approved` \| `rejected`).

| Status | Body |
|--------|------|
| 200 | `TestCaseListResponse` |
| 404 | Story not found |

Use `status=pending_review` for the QA review queue. See [`docs/TestCaseGenerator.md`](./TestCaseGenerator.md) and [`docs/QAApproval.md`](./QAApproval.md).

#### `POST /api/v1/stories/{story_id}/test-cases/approve-all`

Approve all draft / pending_review / rejected test cases for the story. When every case is approved and a workflow run is at `test_cases_generated`, advances the run to `qa_approved`.

| Status | Body |
|--------|------|
| 200 | `TestCaseApproveAllResponse` |
| 400 | No test cases |
| 404 | Story not found |

---

#### `POST /api/v1/stories/{story_id}/bdd/generate`

Run the AI BDD Generator and persist a `BddFeature` (Gherkin). Tags: **Stories**, **AI**, **BDD**.

Optional body:

```json
{
  "logical_model": "default",
  "include_drafts": false
}
```

By default only **approved** test cases are used. Set `include_drafts: true` to also include `draft` and `pending_review` cases.

**Responses**

| Status | Body |
|--------|------|
| 201 | `BddGenerateResponse` (`feature`, `summary`, `provider`, `model`, `source_test_case_count`) |
| 400 | No eligible cases / AI / parse failure |
| 404 | Story not found |

#### `GET /api/v1/stories/{story_id}/bdd`

Paginated BDD features for the story. Query: `page`, `page_size`. Newest first.

| Status | Body |
|--------|------|
| 200 | `BddFeatureListResponse` |
| 404 | Story not found |

See [`docs/BDDGenerator.md`](./BDDGenerator.md).

---

#### `POST /api/v1/stories/{story_id}/playwright/generate`

Run the AI Playwright Generator and persist an `AutomationArtifact` (TypeScript). Tags: **Stories**, **AI**, **Playwright**.

Optional body:

```json
{
  "logical_model": "default",
  "use_bdd": true,
  "use_test_cases": true,
  "include_drafts": false
}
```

Uses BDD features and/or eligible test cases. Browser execution is not performed.

**Responses**

| Status | Body |
|--------|------|
| 201 | `PlaywrightGenerateResponse` (`artifact`, `summary`, `provider`, `model`, `file_count`, source counts) |
| 400 | No eligible sources / AI / parse failure |
| 404 | Story not found |

#### `GET /api/v1/stories/{story_id}/playwright`

Paginated Playwright artifacts for the story. Query: `page`, `page_size`. Newest first.

| Status | Body |
|--------|------|
| 200 | `AutomationArtifactListResponse` |
| 404 | Story not found |

See [`docs/PlaywrightGenerator.md`](./PlaywrightGenerator.md).

---

#### `StoryResponse` fields
| Field | Type |
|-------|------|
| id | UUID |
| project_id | UUID |
| sprint_id | UUID \| null |
| title | string |
| description | string \| null |
| status | enum |
| story_type | enum |
| priority | enum |
| story_points | int \| null |
| external_id | string \| null |
| rank | int \| null |
| created_at | datetime |
| updated_at | datetime |
| created_by | UUID \| null |
| updated_by | UUID \| null |
| is_deleted | bool |
| version | int |

---

### 5.4 Test Cases / QA Approval

Tags: **Test Cases**, **QA Approval**. Full detail: [`docs/QAApproval.md`](./QAApproval.md).

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/test-cases/{id}` | Get test case |
| `PUT` | `/api/v1/test-cases/{id}` | Edit (versioned); approved/rejected → `pending_review` |
| `POST` | `/api/v1/test-cases/{id}/approve` | Approve one; may advance workflow |
| `POST` | `/api/v1/test-cases/{id}/reject` | Reject one (`{"reason": "…"}`) |
| `GET` | `/api/v1/test-cases/{id}/versions` | Version history |

`TestCaseStatus`: `draft`, `pending_review`, `approved`, `rejected`. AI-generated cases start as `pending_review`.

### 5.5 BDD / Gherkin

Tags: **BDD**, **AI**. Full detail: [`docs/BDDGenerator.md`](./BDDGenerator.md).

| Method | Path | Summary |
|--------|------|---------|
| `POST` | `/api/v1/stories/{story_id}/bdd/generate` | Generate + persist Gherkin feature |
| `GET` | `/api/v1/stories/{story_id}/bdd` | List features for story |
| `GET` | `/api/v1/bdd/{id}` | Get feature by id |

Supports Feature, Scenario, Scenario Outline, Examples, and Tags. Default input: approved test cases only.

### 5.6 Playwright / Automation artifacts

Tags: **Playwright**, **AI**. Full detail: [`docs/PlaywrightGenerator.md`](./PlaywrightGenerator.md).

| Method | Path | Summary |
|--------|------|---------|
| `POST` | `/api/v1/stories/{story_id}/playwright/generate` | Generate + persist TS automation |
| `GET` | `/api/v1/stories/{story_id}/playwright` | List artifacts for story |
| `GET` | `/api/v1/playwright/{id}` | Get artifact by id |

Stores page objects, locators, fixtures, utilities, assertions, hooks, and specs as JSON + file content. Browser execution is handled by the Execution Engine (stub runner for MVP).

### 5.7 Execution Engine

Tag: **Executions**. Full detail: [`docs/ExecutionEngine.md`](./ExecutionEngine.md).

| Method | Path | Summary |
|--------|------|---------|
| `POST` | `/api/v1/executions/run` | Stub-run by `story_id` / `automation_artifact_id` / `automation_job_id` |
| `GET` | `/api/v1/executions` | Execution history (filter by job / project / story / status) |
| `GET` | `/api/v1/executions/{id}` | Execution detail |
| `POST` | `/api/v1/executions/{id}/retry` | Retry failed/error/blocked execution |

Persists `AutomationJob` + `Execution` rows. Optional `workflow_run_id` emits `ExecutionStarted` / `ExecutionCompleted`. No real browsers in MVP.

#### Failure Analysis / Jira Bug Creation

See [`docs/FailureAnalysis.md`](./FailureAnalysis.md) and [`docs/JiraBugCreation.md`](./JiraBugCreation.md).

| Method | Path | Summary |
|--------|------|---------|
| `POST` | `/api/v1/executions/{id}/analyze-failure` | AI failure analysis (+ suggested fix) |
| `GET` | `/api/v1/executions/{id}/failure-analysis` | Latest FailureAnalysis |
| `POST` | `/api/v1/executions/{id}/create-jira-bug` | Create Jira Bug + persist local Bug |

### 5.8 Dashboard & Reporting

Tag: **Dashboard**. Full detail: [`docs/Dashboard.md`](./Dashboard.md).

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/dashboard/summary` | Org/project entity counts + status maps |
| `GET` | `/api/v1/dashboard/execution-trends` | Day/week execution outcome buckets |
| `GET` | `/api/v1/dashboard/coverage` | Stories with/without cases + approval ratios |
| `GET` | `/api/v1/dashboard/ai-metrics` | Analyses, AI test cases, BDD, Playwright |

Query: optional `organization_id`, `project_id`. Trends also accept `days` (1–365) and `bucket` (`day`\|`week`).

### 5.9 Notifications

Tag: **Notifications**. Full detail: [`docs/Notifications.md`](./Notifications.md).

| Method | Path | Summary |
|--------|------|---------|
| `POST` | `/api/v1/notifications/send` | Send via `email` / `slack` / `teams` |
| `GET` | `/api/v1/notifications` | Paginated `NotificationLog` history |

Email uses an SMTP stub (log only). Slack/Teams POST to `SLACK_WEBHOOK_URL` / `TEAMS_WEBHOOK_URL`. Optional EventBus hook on `WORKFLOW_COMPLETED` / `WORKFLOW_FAILED`.

### 5.10 Jira Connector

Tag: **Jira Connector** (Swagger `/docs`).

Uses the Connector Framework (`JiraConnector` → Credential Manager). Credentials are process-local (in-memory) until a persistent vault is added.

See also [`docs/JiraIntegration.md`](./JiraIntegration.md).

#### `POST /api/v1/connectors/jira/connect`

Body:

```json
{
  "base_url": "https://your-domain.atlassian.net",
  "email": "you@example.com",
  "api_token": "***",
  "acceptance_criteria_field": "customfield_10000"
}
```

`acceptance_criteria_field` is optional. Validates against Jira (`/myself`) and stores credentials.

#### `POST /api/v1/connectors/jira/disconnect`

Closes the session and clears stored credentials/config for the Jira connector.

#### `GET /api/v1/connectors/jira/health`

Returns framework health: `status`, `version`, `latency_ms`, `last_checked`.

#### `GET /api/v1/connectors/jira/projects`

Lists Jira projects (requires prior connect).

#### `GET /api/v1/connectors/jira/boards`

Query: optional `project_key`.

#### `GET /api/v1/connectors/jira/sprints`

Query: required `board_id`.

#### `POST /api/v1/connectors/jira/sync`

Body:

```json
{
  "organization_id": "uuid",
  "project_keys": ["PAY"],
  "board_id": 123
}
```

Imports projects, sprints, and stories (description, AC, priority, labels, type, status, assignee, reporter, dates). Preserves Jira ids (`external_id`, `jira_issue_id`). Skips unchanged issues via `external_updated_at`. Writes a `SyncHistory` row.

---

### 5.11 GitHub Connector

Tag: **GitHub Connector** (Swagger `/docs`).

Uses the Connector Framework (`GitHubConnector` → Credential Manager with `CredentialType.PAT`). Credentials are process-local (in-memory) until a persistent vault is added.

See also [`docs/GitHubIntegration.md`](./GitHubIntegration.md).

#### `POST /api/v1/connectors/github/connect`

Body:

```json
{
  "personal_access_token": "***",
  "owner": "acme-org",
  "repo": "qa-automation",
  "default_base_branch": "main"
}
```

Validates against GitHub (`GET /user`) and stores credentials + optional defaults.

#### `POST /api/v1/connectors/github/disconnect`

Closes the session and clears stored credentials/config.

#### `GET /api/v1/connectors/github/health`

Returns framework health: `status`, `version`, `latency_ms`, `last_checked`.

#### `POST /api/v1/connectors/github/create-branch`

Creates a branch from `from_branch` (default: connector `default_base_branch` / `main`).

#### `POST /api/v1/connectors/github/commit`

Commits files (explicit list or `automation_artifact_id`) and updates the branch ref (push).

#### `POST /api/v1/connectors/github/push`

Alias of `/commit` — GitHub REST has no separate push.

#### `POST /api/v1/connectors/github/pull-request`

Opens a pull request (`head` → `base`).

#### `GET /api/v1/connectors/github/status-checks`

Query: required `ref` (branch or SHA); optional `owner`, `repo`. Returns combined statuses and check runs.

---

### 5.5 Workflows

Tag: **Workflows**. See [`docs/WorkflowEngine.md`](./WorkflowEngine.md).

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/workflows/start` | Start run for a story |
| POST | `/api/v1/workflows/{id}/advance` | Advance automatic stage |
| POST | `/api/v1/workflows/{id}/approve` | QA approve/reject |
| POST | `/api/v1/workflows/{id}/retry` | Retry from state |
| POST | `/api/v1/workflows/{id}/cancel` | Cancel |
| GET | `/api/v1/workflows/{id}` | Status + logs |
| GET | `/api/v1/workflows/by-story/{story_id}` | Latest by story |

### 5.2 Projects / 5.3 Sprints

Project CRUD: `/api/v1/projects` (+ `/{id}/dashboard`).  
Sprint CRUD: `/api/v1/sprints`. Soft delete; search/filter/paginate.

---

## 6. Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| BAD_REQUEST | 400 | Invalid project/sprint reference or connector request |
| NOT_FOUND | 404 | Resource not found |
| VALIDATION_ERROR | 422 | Request validation failed |
| DATABASE_ERROR | 500 | Database failure |
| INTERNAL_ERROR | 500 | Unexpected error |

Connector failures surface as 400/502-style application errors when Jira auth or upstream calls fail (see endpoint responses in Swagger).

---

## 7. Swagger / OpenAPI

| URL | Description |
|-----|-------------|
| `/docs` | Swagger UI — Stories, Dashboard, Notifications, AI, Workflows, Executions, Jira, … |
| `/redoc` | ReDoc |
| `/openapi.json` | OpenAPI 3 schema |

### Frontend consumer

Milestone 6 Story Management UI (`/stories`) uses Story endpoints via Axios + TanStack Query. See [`frontend/docs/StoryManagement.md`](../frontend/docs/StoryManagement.md). Jira connect UI is not in this milestone.

---

## 8. Rate Limiting

API gateway rate limiting is not implemented. The Jira HTTP client retries `429` using `Retry-After` / exponential backoff.

---

## 9. Webhooks

Not implemented (Jira sync is pull-based via `POST .../sync`).
