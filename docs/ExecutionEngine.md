# Execution Engine

## Document Information

| Field | Value |
|-------|-------|
| Milestone | Execution Engine (Milestone 17) |
| Status | **Complete** (REST; stub + local Playwright CLI; workflow agent; browsers optional via `runner=playwright`) |
| Last Updated | 2026-07-21 |
| Package | `backend/app/services/execution_engine.py` + related layers |

---

## 1. Purpose

Run generated / approved tests and persist results on existing domain models:

- `AutomationJob` — batch run (status, timing, config)
- `Execution` — per-test-case outcome (pass/fail, duration, evidence, retries)

MVP ships two runners:

- **`stub`** (default) — `StubTestRunner` records deterministic pass/fail **without** browsers
- **`playwright`** — `PlaywrightLocalRunner` materializes generated artifact files and runs `npx playwright test`

Optional: when `workflow_run_id` is provided (and the run is in `pull_request_created`), emit:

1. `ExecutionStarted` → `execution_started`
2. `ExecutionCompleted` → `execution_completed`

---

## 2. Clean Architecture

```
schema (execution.py)
  → repository (automation_job.py, execution.py)
    → service (execution_engine.py) + StubTestRunner
      → endpoint (executions.py) + ExecutionAgent
```

| Layer | Module |
|-------|--------|
| Models | `app/models/automation_job.py`, `app/models/execution.py` (existing) |
| Runner | `app/execution/stub_runner.py`, `app/execution/playwright_runner.py`, `app/execution/factory.py` |
| Schema | `app/schemas/execution.py` |
| Repository | `app/repositories/automation_job.py`, `app/repositories/execution.py` |
| Service | `app/services/execution_engine.py` |
| Agent | `app/orchestration/agents/execution.py` |
| API | `POST/GET /api/v1/executions…` |

**Out of scope:** BrowserStack / cloud grids, CI matrix runners, full CD promotion pipelines, video artifacts beyond Playwright defaults.

---

## 3. API

Swagger tag: **Executions**.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/executions/run` | Start a stub run |
| `GET` | `/api/v1/executions` | Execution history (filter + paginate) |
| `GET` | `/api/v1/executions/{id}` | Execution detail (+ job summary) |
| `POST` | `/api/v1/executions/{id}/retry` | Retry failed/error/blocked execution |

### `POST /api/v1/executions/run`

Provide **exactly one** target:

```json
{
  "story_id": "uuid",
  "workflow_run_id": "uuid",
  "include_drafts": false,
  "runner": "stub",
  "force_fail_test_case_ids": [],
  "name": "optional job name",
  "config": {}
}
```

Set `"runner": "playwright"` (and preferably `automation_artifact_id`) to execute generated specs via the local Playwright CLI. Without Node/`npx playwright`, cases are marked `error` with an install hint (no silent stub fallback).

Alternatives: `automation_artifact_id` or `automation_job_id` (instead of `story_id`).

| Target | Behavior |
|--------|----------|
| `story_id` | Approved test cases (or all if `include_drafts`) |
| `automation_artifact_id` | Artifact `source_test_case_ids`, else story cases |
| `automation_job_id` | Pending/queued job is executed in place; otherwise a new job clones the case set |

Returns `201` + `ExecutionRunResponse` (`job` with nested executions + counts).

### Stub failure rules

1. `test_case.id` in `force_fail_test_case_ids`
2. Title contains `"fail"` (case-insensitive)
3. Otherwise **PASSED**

### Retry

`POST /api/v1/executions/{id}/retry` re-runs in place, increments `retry_count`, refreshes parent `AutomationJob` aggregate status.

---

## 4. Workflow integration

| Event | From state | To state |
|-------|------------|----------|
| `execution_started` | `pull_request_created` | `execution_started` |
| `execution_completed` | `execution_started` | `execution_completed` |

- **REST**: pass `workflow_run_id` on `/run` (must be `pull_request_created`).
- **Agent** `ExecutionAgent`: registered for `pull_request_created`; on `advance`, runs the stub suite, applies `ExecutionStarted`, then emits `ExecutionCompleted`.

Job-level status:

- All passed → `AutomationJob.status = completed`
- Any failed/error/blocked → `failed`

Mixed pass/fail still emits `ExecutionCompleted` (suite finished); failure analysis is a later milestone.

---

## 5. Schema notes

`automation_jobs` / `executions` tables already exist (domain schema). No Alembic revision required for this milestone.

`AutomationJob.config` uses portable SQLAlchemy `JSON` (stores story/artifact/test_case ids and runner metadata).

---

## 6. Tests

```bash
cd backend && python -m pytest tests/test_execution_engine.py -q
```

Covers stub rules, run-by-story/artifact/job, list/get/retry, validation, and workflow event emission.
