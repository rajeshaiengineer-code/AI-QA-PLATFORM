# Jira Bug Creation

## Document Information

| Field | Value |
|-------|-------|
| Milestone | Jira Bug Creation (Milestone 19) |
| Status | **Complete** (REST MVP; Jira connector create_issue; workflow agent) |
| Last Updated | 2026-07-16 |
| Package | `backend/app/services/bug_creation.py` + related layers |

---

## 1. Purpose

Create a Jira Bug from a failed `Execution` and its `FailureAnalysis`, then
persist a local `Bug` with:

- `external_id` — Jira issue key (e.g. `QA-42`)
- `extra_metadata` — summary, logs link, execution link, Jira URL, analysis fields

Uses the existing `JiraConnector` / `JiraClient` (`create_issue`).

---

## 2. Clean Architecture

```
schema (bug.py)
  → repository (bug.py)
    → service (bug_creation.py) + JiraConnector
      → endpoint (executions.py) + BugCreationAgent
```

| Layer | Module |
|-------|--------|
| Model | `app/models/bug.py` (extended) |
| Schema | `app/schemas/bug.py` |
| Repository | `app/repositories/bug.py` |
| Service | `app/services/bug_creation.py` |
| Client | `app/connectors/jira/client.py` → `create_issue` |
| Agent | `app/orchestration/agents/bug_creation.py` |
| API | `POST /api/v1/executions/{id}/create-jira-bug` |

**Prerequisite:** Jira connected via `POST /api/v1/connectors/jira/connect`
(or inject a connector in tests).

---

## 3. API

Swagger tags: **Executions**, **Jira Connector**.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/executions/{id}/create-jira-bug` | File Jira bug + persist Bug |

### Request body

```json
{
  "jira_project_key": "QA",
  "failure_analysis_id": null,
  "title": null,
  "description": null,
  "priority": "high",
  "issue_type": "Bug",
  "logs_url": "stub://logs/run-1.txt",
  "execution_url": "/api/v1/executions/<id>",
  "labels": ["ai-qa", "auto-filed"]
}
```

When `failure_analysis_id` is omitted, the latest analysis for the execution is used
(if any). Title/description default from analysis + execution evidence.

### Response

```json
{
  "bug": { "id": "...", "external_id": "QA-42", "extra_metadata": { ... } },
  "jira_key": "QA-42",
  "jira_id": "10042",
  "jira_url": "https://acme.atlassian.net/browse/QA-42"
}
```

---

## 4. Workflow integration

| Event | From state | To state |
|-------|------------|----------|
| `bug_created` | `failure_analyzed` | `completed` |

- **Agent** `BugCreationAgent`: registered for `failure_analyzed`.
  - Requires `jira_project_key` in agent input; otherwise emits `report_published`
    (skip filing).

---

## 5. Tests

```bash
cd backend && python -m pytest tests/test_jira_bug_creation.py -q
```

Jira HTTP is mocked via a `MockJiraClient` — no live Atlassian credentials.
