# AI BDD Generator

## Document Information

| Field | Value |
|-------|-------|
| Milestone | AI BDD Generator (Milestone 14) |
| Status | **Complete** (REST MVP; workflow agent registered) |
| Last Updated | 2026-07-16 |
| Package | `backend/app/services/bdd_generator.py` + related layers |

---

## 1. Purpose

Generate **Gherkin / Cucumber feature files** from a story’s test cases using the AI Framework, and persist them as `BddFeature` rows.

Supported constructs:

| Construct | Notes |
|-----------|--------|
| `Feature` | Name, optional description, feature-level tags |
| `Scenario` | Concrete Given/When/Then steps |
| `Scenario Outline` | Parameterized steps with placeholders |
| `Examples` | Header + rows table (required for outlines) |
| `Tags` | `@tag` style on feature, scenario, and examples |

By default only **approved** test cases are used. Pass `include_drafts=true` to also include `draft` and `pending_review` cases (rejected cases are never included).

The workflow agent emits `bdd_generated` after QA approval (`story_approved`).

---

## 2. Clean Architecture

```
schema (bdd_feature.py)
  → repository (bdd_feature.py)
    → service (bdd_generator.py)
      → endpoint (stories.py, bdd.py) + BddGeneratorAgent
```

| Layer | Module |
|-------|--------|
| Model | `app/models/bdd_feature.py` (`bdd_features` table) |
| Schema | `app/schemas/bdd_feature.py` |
| Repository | `app/repositories/bdd_feature.py` |
| Service | `app/services/bdd_generator.py` |
| Prompt | `app/ai/prompts/templates/bdd_generate.txt` |
| Agent | `app/orchestration/agents/bdd_generator.py` |
| API | `POST …/bdd/generate`, `GET …/bdd`, `GET /api/v1/bdd/{id}` |

---

## 3. API

### `POST /api/v1/stories/{story_id}/bdd/generate`

Triggers generation and persistence. Optional body:

```json
{
  "logical_model": "fast",
  "include_drafts": false
}
```

Defaults: logical model `default`; `include_drafts=false` (approved only). Returns `201` + `BddGenerateResponse`.

### `GET /api/v1/stories/{story_id}/bdd`

Paginated list of BDD features for the story (`page`, `page_size`). Newest first.

### `GET /api/v1/bdd/{id}`

Fetch a single persisted feature (including full `gherkin_content`).

Swagger tags: **Stories**, **AI**, **BDD**.

---

## 4. AI flow

1. Load story + acceptance criteria
2. Select eligible test cases (approved, or + drafts when flagged)
3. Render `bdd_generate` prompt via `PromptManager`
4. Resolve provider via `ModelRegistry` + `AIProviderFactory` (or injected mock)
5. `provider.generate(...)` → parse JSON (tolerates markdown fences + aliases)
6. Validate with `BddGenerateResult` → render Gherkin → persist `BddFeature`

Provider failures, missing eligible cases, and invalid JSON map to HTTP `400` (`BAD_REQUEST`).

---

## 5. Workflow agent

`BddGeneratorAgent` is registered at app startup (`register_builtin_agents()`):

- Listens for `story_approved` (run is in `qa_approved`)
- On workflow `advance`, generates BDD using the engine session
- Emits `bdd_generated` (or `bdd_failed` on error)

**MVP primary path is REST.**

---

## 6. Migration

```bash
cd backend
alembic upgrade head
```

Revision: `bdd_gen_001` — creates `bdd_features`.

---

## 7. Tests

```bash
cd backend
source venv/bin/activate
pytest tests/test_bdd_generator.py -v
```

All LLM calls use a `MockAIProvider`; no real API keys are required.
