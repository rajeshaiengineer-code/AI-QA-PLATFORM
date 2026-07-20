# AI Playwright Generator

## Document Information

| Field | Value |
|-------|-------|
| Milestone | AI Playwright Generator (Milestone 15) |
| Status | **Complete** (REST MVP; workflow agent registered; no browser execution) |
| Last Updated | 2026-07-16 |
| Package | `backend/app/services/playwright_generator.py` + related layers |

---

## 1. Purpose

Generate **Playwright TypeScript** automation from a story’s **BDD features** and/or **approved test cases**, and persist them as `AutomationArtifact` rows.

Artifact groups (each a JSON array of `{path, content, description?}`):

| Group | Typical paths |
|-------|----------------|
| `page_objects` | `pages/*.ts` |
| `locators` | `locators/*.ts` |
| `fixtures` | `fixtures/*.ts` |
| `utilities` | `utils/*.ts` |
| `assertions` | `assertions/*.ts` |
| `hooks` | `hooks/*.ts` |
| `specs` | `tests/*.spec.ts` |

Defaults: `use_bdd=true`, `use_test_cases=true`, `include_drafts=false` (approved cases only). At least one eligible source is required.

The workflow agent emits `automation_generated` after BDD is ready (`bdd_generated`).

**Out of scope for this milestone:** real browser execution, CI runners, writing files to disk.

---

## 2. Clean Architecture

```
schema (automation_artifact.py)
  → repository (automation_artifact.py)
    → service (playwright_generator.py)
      → endpoint (stories.py, playwright.py) + PlaywrightGeneratorAgent
```

| Layer | Module |
|-------|--------|
| Model | `app/models/automation_artifact.py` (`automation_artifacts` table) |
| Schema | `app/schemas/automation_artifact.py` |
| Repository | `app/repositories/automation_artifact.py` |
| Service | `app/services/playwright_generator.py` |
| Prompt | `app/ai/prompts/templates/playwright_generate.txt` |
| Agent | `app/orchestration/agents/playwright_generator.py` |
| Connector stub | `app/connectors/playwright/` (execution deferred) |
| API | `POST …/playwright/generate`, `GET …/playwright`, `GET /api/v1/playwright/{id}` |

---

## 3. API

### `POST /api/v1/stories/{story_id}/playwright/generate`

Triggers generation and persistence. Optional body:

```json
{
  "logical_model": "fast",
  "use_bdd": true,
  "use_test_cases": true,
  "include_drafts": false
}
```

Returns `201` + `PlaywrightGenerateResponse`.

### `GET /api/v1/stories/{story_id}/playwright`

Paginated list of automation artifacts for the story (`page`, `page_size`). Newest first.

### `GET /api/v1/playwright/{id}`

Fetch a single persisted artifact (including all file content strings).

Swagger tags: **Stories**, **AI**, **Playwright**.

---

## 4. AI flow

1. Load story + acceptance criteria
2. Optionally load BDD features and/or eligible test cases
3. Render `playwright_generate` prompt via `PromptManager`
4. Resolve provider via `ModelRegistry` + `AIProviderFactory` (or injected mock)
5. `provider.generate(...)` → parse JSON (tolerates markdown fences + aliases)
6. Validate with `PlaywrightGenerateResult` → persist `AutomationArtifact`

Provider failures, missing sources, and invalid JSON map to HTTP `400` (`BAD_REQUEST`).

---

## 5. Workflow agent

`PlaywrightGeneratorAgent` is registered at app startup (`register_builtin_agents()`):

- Listens for `bdd_generated` (run is in `bdd_generated`)
- On workflow `advance`, generates Playwright using the engine session
- Emits `automation_generated` (or `automation_failed` on error)

**MVP primary path is REST.**

---

## 6. Migration

```bash
cd backend
alembic upgrade head
```

Revision: `pw_gen_001` — creates `automation_artifacts`.

---

## 7. Tests

```bash
cd backend
source venv/bin/activate
pytest tests/test_playwright_generator.py -v
```

All LLM calls use a `MockAIProvider`; no real API keys are required.
