# Dashboard & Reporting

## Document Information

| Field | Value |
|-------|-------|
| Milestone | Dashboard & Reporting (Milestone 18) |
| Status | **Complete** (REST aggregates + optional Next.js page) |
| Last Updated | 2026-07-16 |
| Package | `backend/app/services/dashboard.py` + related layers |

> Note: Execution Engine is Milestone 17. This reporting milestone is numbered **18** on the roadmap (follows persisted Executions).

---

## 1. Purpose

Org/project-scoped quality metrics without a heavy charting library:

- Entity summary counts
- Execution outcome time series
- Story ↔ test-case coverage + approval ratios
- AI pipeline artifact counts

---

## 2. Clean Architecture

```
schema (dashboard.py)
  → repository (dashboard.py)
    → service (dashboard.py)
      → endpoint (dashboard.py)
```

| Layer | Module |
|-------|--------|
| Schema | `app/schemas/dashboard.py` |
| Repository | `app/repositories/dashboard.py` |
| Service | `app/services/dashboard.py` |
| API | `app/api/v1/endpoints/dashboard.py` |
| UI | `frontend/src/app/dashboard/page.tsx` |

**Out of scope:** auth/RBAC, export/CSV, real-time websockets, third-party chart SDKs.

---

## 3. API

Swagger tag: **Dashboard**. Base path: `/api/v1/dashboard`.

Common query params:

| Param | Type | Notes |
|-------|------|-------|
| `organization_id` | UUID | Optional org scope |
| `project_id` | UUID | Optional project scope; must belong to org when both set |

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/dashboard/summary` | Counts + status breakdowns |
| `GET` | `/api/v1/dashboard/execution-trends` | Day/week buckets over last N days |
| `GET` | `/api/v1/dashboard/coverage` | Stories with/without cases + approval ratios |
| `GET` | `/api/v1/dashboard/ai-metrics` | Analyses, AI cases, BDD, Playwright |

### Summary

Returns `project_count`, `sprint_count`, `story_count`, `test_case_count`, `execution_count`, `automation_job_count`, plus `stories_by_status` and `executions_by_status`.

### Execution trends

| Param | Default | Notes |
|-------|---------|-------|
| `days` | `30` | 1–365 |
| `bucket` | `day` | `day` or `week` |

Buckets include `total`, `passed`, `failed`, `error`, `skipped`, `other`.

### Coverage

- `stories_with_test_cases` / `stories_without_test_cases`
- Status counts for draft / pending_review / approved / rejected
- `coverage_ratio`, `approved_ratio` (0–1)

### AI metrics

- `analyses_count` — `StoryAnalysis` rows
- `generated_test_cases` — `TestCase.source == ai`
- `bdd_artifacts` — `BddFeature` rows
- `playwright_artifacts` — `AutomationArtifact` rows

---

## 4. Frontend

- Route: `/dashboard` (enabled in sidebar)
- Component: `ReportingDashboard` — uses AppShell tokens (`accent` teal, surface, border)
- Optional project filter via projects list

---

## 5. Tests

`backend/tests/test_dashboard.py` — summary, trends, coverage, AI metrics, scope validation.
