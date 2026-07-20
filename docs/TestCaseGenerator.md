# AI Test Case Generator

## Document Information

| Field | Value |
|-------|-------|
| Milestone | AI Test Case Generator |
| Status | **Complete** (REST MVP; workflow agent registered) |
| Last Updated | 2026-07-16 |
| Package | `backend/app/services/test_case_generator.py` + related layers |

---

## 1. Purpose

Generate full **TestCase** entities from a user story (plus acceptance criteria and optional latest `StoryAnalysis`) using the AI Framework.

Categories persisted on each case:

| Category | Intent |
|----------|--------|
| `positive` | Happy-path / functional success |
| `negative` | Invalid input / failure paths |
| `boundary` | Edge / limit values |
| `api` | API contract / status / payload |
| `security` | AuthZ, injection, token safety |
| `database` | Persistence / integrity |
| `accessibility` | Keyboard / a11y |
| `performance` | Latency / SLA |

QA approval UI/workflow is covered in [`docs/QAApproval.md`](./QAApproval.md). The generator agent emits `test_cases_generated` for the workflow engine; cases are persisted with `status=pending_review`.

---

## 2. Clean Architecture

```
schema (test_case.py)
  → repository (test_case.py)
  → service (test_case_generator.py)
  → endpoint (stories.py) + TestCaseGeneratorAgent
```

| Layer | Module |
|-------|--------|
| Model | `app/models/test_case.py` (+ `category`, `source`, `tags`, `provider`, `model`) |
| Enums | `TestCaseCategory`, `TestCaseSource` in `app/models/enums.py` |
| Schema | `app/schemas/test_case.py` |
| Repository | `app/repositories/test_case.py` |
| Service | `app/services/test_case_generator.py` |
| Prompt | `app/ai/prompts/templates/test_case_generate.txt` |
| Agent | `app/orchestration/agents/test_case_generator.py` |
| API | `POST …/test-cases/generate`, `GET …/test-cases` |

---

## 3. API

### `POST /api/v1/stories/{story_id}/test-cases/generate`

Triggers generation and persistence. Optional body:

```json
{
  "logical_model": "fast",
  "categories": ["positive", "security"]
}
```

Defaults: logical model `default`; all eight categories. Returns `201` + `TestCaseGenerateResponse`.

### `GET /api/v1/stories/{story_id}/test-cases`

Paginated list (`page`, `page_size`). Optional filters: `category`, `source`.

Swagger tags: **Stories**, **AI**, **Test Cases**.

---

## 4. AI flow

1. Load story + acceptance criteria (+ latest analysis if any)
2. Render `test_case_generate` prompt via `PromptManager`
3. Resolve provider via `ModelRegistry` + `AIProviderFactory` (or injected mock)
4. `provider.generate(...)` → parse JSON (tolerates markdown fences + aliases)
5. Validate with `TestCaseGenerateResult` → persist `TestCase` rows (`source=ai`)

Provider failures and invalid JSON map to HTTP `400` (`BAD_REQUEST`).

---

## 5. Workflow agent

`TestCaseGeneratorAgent` is registered at app startup (`register_builtin_agents()`):

- Listens for `story_analyzed`
- On workflow `advance`, generates cases using the engine session
- Emits `test_cases_generated` (or `test_gen_failed` on error)

**MVP primary path is REST.**

---

## 6. Migration

```bash
cd backend
alembic upgrade head
```

Revision: `test_case_gen_001` — adds `category`, `source`, `tags`, `provider`, `model` on `test_cases`.

---

## 7. Tests

```bash
cd backend
source venv/bin/activate
pytest tests/test_test_case_generator.py -v
```

All LLM calls use a `MockAIProvider`; no real API keys are required.
