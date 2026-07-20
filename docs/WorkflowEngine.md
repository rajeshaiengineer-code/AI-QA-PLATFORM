# Workflow Engine

## Document Information

| Field | Value |
|-------|-------|
| Status | Implemented (runtime) |
| Package | `backend/app/orchestration/` |
| Last Updated | 2026-07-16 |

---

## 1. Overview

Event-driven orchestrator for the story → tests → automation → execution pipeline.

- Only `WorkflowEngine` mutates `WorkflowState`
- Agents emit events; they never set state
- In-process `EventBus` (durable broker later)
- Persisted `workflow_runs` + `workflow_logs`
- Retry policy for retryable agent failures

---

## 2. API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/workflows/start` | Create run (`NEW` → `SYNCED` by default) |
| POST | `/api/v1/workflows/{id}/advance` | Next automatic stage |
| POST | `/api/v1/workflows/{id}/approve` | QA gate |
| POST | `/api/v1/workflows/{id}/retry` | Reset to a non-terminal state |
| POST | `/api/v1/workflows/{id}/cancel` | Cancel run |
| GET | `/api/v1/workflows/{id}` | Status + logs |
| GET | `/api/v1/workflows/by-story/{story_id}` | Latest run for story |

Swagger tag: **Workflows**.

---

## 3. Key files

| Path | Role |
|------|------|
| `orchestration/state/` | `WorkflowState` + transition table |
| `orchestration/events/` | `WorkflowEvent`, `DomainEvent`, `InProcessEventBus` |
| `orchestration/agents/` | Agent port + `AgentRegistry` |
| `orchestration/engine/` | `WorkflowEngine`, `RetryPolicy` |
| `models/workflow_run.py` | Persistence |
| `models/workflow_log.py` | Transition / action logs |

---

## 4. Notes

- Advance is blocked at `test_cases_generated` until `approve`
- Without registered agents, `advance` applies happy-path auto events (for MVP/testing)
- Built-in agents: Story Analyzer, Test Case Generator, BDD Generator, Playwright Generator, GitHub PR (`pull_request_created`), Execution (`pull_request_created` → run stub suite), Failure Analysis (`execution_completed`), Bug Creation (`failure_analyzed`)
