# Production Readiness

## Document Information

| Field | Value |
|-------|-------|
| Status | Implemented (Milestone 22) |
| Last Updated | 2026-07-16 |

---

## 1. Overview

Hardening checklist for running the AI QA Platform beyond local demos: CI, containers, config validation, health probes, logging, DB pools, and secrets handling.

Companion docs:

- [`SecurityChecklist.md`](./SecurityChecklist.md) — security review checklist
- [`Deployment.md`](./Deployment.md) — deploy / migrate / rollback notes
- [`Authentication.md`](./Authentication.md) — JWT + RBAC (`AUTH_ENABLED`)

---

## 2. CI (GitHub Actions)

Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

| Job | Checks |
|-----|--------|
| Backend | `pip install -r requirements.txt` → `pytest` |
| Frontend | `npm ci` → `lint` → `typecheck` (`tsc --noEmit`) → `vitest` |

Runs on push/PR to `main`, `develop`, and `master`.

---

## 3. Required environment variables

Copy examples; **never commit real `.env` files** (see Secrets below).

### Backend (`backend/.env.example`)

| Variable | Required | Notes |
|----------|----------|--------|
| `DATABASE_URL` | Yes | Async SQLAlchemy URL (`postgresql+asyncpg://…`) |
| `SECRET_KEY` | Yes (prod) | ≥32 random chars; startup rejects placeholders when `ENVIRONMENT=production` |
| `ENVIRONMENT` | Yes | `development` \| `test` \| `staging` \| `production` |
| `DEBUG` | Prod: `false` | Startup fails if `true` in production |
| `LOG_FORMAT` | Prod: `json` | `json` (preferred) or `text` |
| `LOG_LEVEL` | No | Default `INFO` |
| `DATABASE_POOL_SIZE` | No | Default `5` — see §7 |
| `DATABASE_MAX_OVERFLOW` | No | Default `10` |
| `DATABASE_POOL_TIMEOUT` | No | Default `30` seconds |
| `CORS_ORIGINS` | Yes (prod) | Explicit origins; avoid `*` with credentials |
| `AUTH_ENABLED` | Recommended prod `true` | JWT gate for protected routes |
| `AI_*_API_KEY` | If using AI | Prefer secret manager; optional at boot |

### Frontend (`frontend/.env.example`)

| Variable | Required | Notes |
|----------|----------|--------|
| `NEXT_PUBLIC_API_URL` | Yes | Public API base (e.g. `https://api.example.com/api/v1`) |

### Compose root (`.env.example`)

Used by `docker-compose.yml` for `DB_*`, `SECRET_KEY`, ports, and shared toggles.

Startup validation lives in `backend/app/core/validation.py` and runs during FastAPI lifespan.

---

## 4. Secrets guidance

- **Do not** commit `.env`, API tokens, PAT/JWT secrets, or cloud keys. Repo ignores `.env*` except `*.example`.
- Use GitHub Actions secrets / cloud secret managers for CI and production.
- Rotate `SECRET_KEY` and connector credentials after any leak.
- Prefer short-lived tokens for Jira/GitHub connectors; store connector secrets outside git.
- See [`SecurityChecklist.md`](./SecurityChecklist.md).

---

## 5. Health & readiness

| Probe | Path | Behavior |
|-------|------|----------|
| Liveness | `GET /api/v1/health/live` | Process up → `200` |
| Health | `GET /api/v1/health` | Process up → `200` (no dependency checks) |
| Readiness | `GET /api/v1/health/ready` | Runs `SELECT 1` against DB; **`503` if DB unhealthy** |

Docker Compose backend healthcheck uses `/ready`. Image `HEALTHCHECK` uses `/live` so a bad dependency does not force an endless restart loop without orchestration policy.

---

## 6. Logging

Configured in `backend/app/core/logging.py`:

| `LOG_FORMAT` | Output |
|--------------|--------|
| `json` | One JSON object per line (`timestamp`, `level`, `logger`, `message`, optional `request_id`) |
| `text` | Human-readable lines for local development |

Production should use `LOG_FORMAT=json` and `LOG_LEVEL=INFO` (or `WARNING`). Correlation IDs are attached via middleware (`X-Request-Id`).

---

## 7. Database pool (performance)

SQLAlchemy async engine (`backend/app/core/database.py`) uses:

| Setting | Default | Guidance |
|---------|---------|----------|
| `DATABASE_POOL_SIZE` | `5` | Baseline concurrent connections per process |
| `DATABASE_MAX_OVERFLOW` | `10` | Extra burst connections |
| `DATABASE_POOL_TIMEOUT` | `30` | Seconds to wait for a free connection |
| `pool_pre_ping` | enabled | Drop stale connections |

Tune pool size ≈ `(workers × pool_size) + overflow` under Postgres `max_connections`. Prefer horizontal workers over huge pools.

---

## 8. Docker

- Backend / frontend Dockerfiles are **multi-stage** (builder + slim runtime).
- Compose wires Postgres + backend + frontend with **healthchecks** and `depends_on: condition: service_healthy`.
- Local compose mounts source and runs uvicorn/Next with reload; production should run image `CMD` without bind mounts and without `--reload`.

```bash
docker compose build
docker compose up -d
docker compose ps   # confirm healthy
```

---

## 9. Pre-production checklist (short)

1. Set strong `SECRET_KEY`, `DEBUG=false`, `ENVIRONMENT=production`, `LOG_FORMAT=json`
2. Enable `AUTH_ENABLED=true` and create an admin user
3. Restrict `CORS_ORIGINS` to real frontends
4. Run Alembic migrations; verify `/api/v1/health/ready`
5. Confirm CI green on the release branch
6. Walk through [`SecurityChecklist.md`](./SecurityChecklist.md)
