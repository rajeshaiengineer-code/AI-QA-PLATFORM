# AI Failure Analysis

## Document Information

| Field | Value |
|-------|-------|
| Milestone | AI Failure Analysis (Milestone 18) |
| Status | **Complete** (REST MVP; AI Framework; workflow agent registered) |
| Last Updated | 2026-07-16 |
| Package | `backend/app/services/failure_analyzer.py` + related layers |

---

## 1. Purpose

Analyze failed `Execution` results with the AI Framework and persist a structured
`FailureAnalysis` including root cause classification and a **suggested fix**.

Optional evidence on the request (may be stub paths/URLs):

- `logs`
- `screenshot_url`
- `video_url`
- `network_url`
- `trace_url`

---

## 2. Clean Architecture

```
schema (failure_analysis.py)
  → repository (failure_analysis.py)
    → service (failure_analyzer.py) + AI Framework
      → endpoint (executions.py) + FailureAnalysisAgent
```

| Layer | Module |
|-------|--------|
| Model | `app/models/failure_analysis.py` |
| Schema | `app/schemas/failure_analysis.py` |
| Repository | `app/repositories/failure_analysis.py` |
| Service | `app/services/failure_analyzer.py` |
| Prompt | `app/ai/prompts/templates/failure_analyze.txt` |
| Agent | `app/orchestration/agents/failure_analysis.py` |
| API | `POST/GET /api/v1/executions/{id}/analyze-failure` / `failure-analysis` |

**Out of scope:** real screenshot/video capture, frontend UI.

---

## 3. API

Swagger tags: **Executions**, **AI**.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/executions/{id}/analyze-failure` | Analyze + persist |
| `GET` | `/api/v1/executions/{id}/failure-analysis` | Latest analysis |

Only `failed`, `error`, and `blocked` executions are analyzable.

### Request body (optional)

```json
{
  "logical_model": "default",
  "logs": "stub://logs/run-1.txt",
  "screenshot_url": "stub://screenshots/fail-1.png",
  "video_url": "stub://videos/fail-1.webm",
  "network_url": "stub://network/fail-1.har",
  "trace_url": "stub://traces/fail-1.zip"
}
```

### Response highlights

| Field | Description |
|-------|-------------|
| `category` | `product_bug` \| `test_bug` \| `flaky` \| `environment` \| `timeout` \| `unknown` |
| `suggested_fix` | Concrete remediation hint |
| `root_cause` | Technical cause summary |
| `confidence` | 0–1 model confidence |

---

## 4. Workflow integration

| Event | From state | To state |
|-------|------------|----------|
| `failure_analyzed` | `execution_completed` | `failure_analyzed` |

- **Agent** `FailureAnalysisAgent`: registered for `execution_completed`.
  - Failed executions → analyze → emit `failure_analyzed`
  - No failures → emit `report_published` (happy path)

---

## 5. Schema / Alembic

Revision `fail_bug_001` creates `failure_analyses` and extends `bugs`
(`failure_analysis_id`, `metadata`).

---

## 6. Tests

```bash
cd backend && python -m pytest tests/test_failure_analysis.py -q
```

AI provider HTTP is mocked — no live API keys required.
