# AI Story Analyzer

## Document Information

| Field | Value |
|-------|-------|
| Milestone | AI Story Analyzer |
| Status | **Complete** (REST MVP; workflow agent registered) |
| Last Updated | 2026-07-16 |
| Package | `backend/app/services/story_analyzer.py` + related layers |

---

## 1. Purpose

Analyze a user story with the AI Framework and persist structured QA planning signals:

| Field | Description |
|-------|-------------|
| `complexity` | `low` / `medium` / `high` |
| `risk` | `low` / `medium` / `high` / `critical` |
| `automation_candidate` | Whether the story is a good automation fit |
| `dependencies` | Likely systems / teams / story dependencies |
| `suggested_tests` | Lightweight test ideas (not full TestCase entities) |
| `summary` / `notes` | Intent summary and clarifying notes |

Full test-case generation is covered by [`docs/TestCaseGenerator.md`](./TestCaseGenerator.md).

---

## 2. Clean Architecture

```
schema (story_analysis.py)
  → repository (story_analysis.py)
  → service (story_analyzer.py)
  → endpoint (stories.py) + StoryAnalyzerAgent
```

| Layer | Module |
|-------|--------|
| Model | `app/models/story_analysis.py` (`story_analyses` table) |
| Schema | `app/schemas/story_analysis.py` |
| Repository | `app/repositories/story_analysis.py` |
| Service | `app/services/story_analyzer.py` |
| Prompt | `app/ai/prompts/templates/story_analyze.txt` |
| Agent | `app/orchestration/agents/story_analyzer.py` |
| API | `POST/GET /api/v1/stories/{story_id}/analyze` / `analysis` |

---

## 3. API

### `POST /api/v1/stories/{story_id}/analyze`

Triggers analysis. Optional body:

```json
{ "logical_model": "fast" }
```

Defaults to logical model `default` from `ModelRegistry`. Returns `201` + `StoryAnalysisResponse`.

### `GET /api/v1/stories/{story_id}/analysis`

Returns the **latest** analysis for the story (`created_at` desc). `404` if none exists.

Swagger tags: **Stories**, **AI**.

---

## 4. AI flow

1. Load story (+ acceptance criteria ordered by `order_index`)
2. Render `story_analyze` prompt via `PromptManager`
3. Resolve provider via `ModelRegistry` + `AIProviderFactory` (or injected mock)
4. `provider.generate(...)` → parse JSON (tolerates markdown fences)
5. Validate with `StoryAnalysisResult` → persist `StoryAnalysis`

Provider failures and invalid JSON map to HTTP `400` (`BAD_REQUEST`).

---

## 5. Workflow agent

`StoryAnalyzerAgent` is registered at app startup (`register_builtin_agents()`):

- Listens for `story_imported` / `story_synced`
- On workflow `advance`, runs analysis using the engine session
- Emits `story_analyzed` (or `analysis_failed` on error)

**MVP primary path is REST.** The agent is available so advance can invoke analysis when the run is in `synced`.

---

## 6. Migration

```bash
cd backend
alembic upgrade head
```

Revision: `story_analysis_001` → table `story_analyses`.

---

## 7. Tests

```bash
cd backend
source venv/bin/activate
pytest tests/test_story_analyzer.py -v
```

All LLM calls use a `MockAIProvider`; no real API keys are required.
