# Deployment Guide

## Document Information

| Field | Value |
|-------|-------|
| Version | 1.1 |
| Last Updated | 2026-07-16 |

Related: [`ProductionReadiness.md`](./ProductionReadiness.md), [`SecurityChecklist.md`](./SecurityChecklist.md)

---

## 1. Overview

Deploy the platform as three services: **PostgreSQL**, **FastAPI backend**, and **Next.js frontend**. Local/staging uses Docker Compose; production should use the same images behind TLS with secrets injected by the host/orchestrator.

---

## 2. Environments

### 2.1 Development

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| Database | localhost:5432 |

### 2.2 Staging / Production

| Concern | Guidance |
|---------|----------|
| `ENVIRONMENT` | `staging` or `production` |
| `DEBUG` | `false` |
| `LOG_FORMAT` | `json` |
| `AUTH_ENABLED` | `true` (recommended) |
| Secrets | Secret manager / compose secrets — not git |

---

## 3. Docker Deployment

### 3.1 Build Images

```bash
docker compose build
```

### 3.2 Run Services

```bash
# Copy env template and set SECRET_KEY / DB_PASSWORD first
cp .env.example .env
docker compose up -d
docker compose ps
```

### 3.3 View Logs

```bash
docker compose logs -f backend
```

Backend/frontend Dockerfiles are multi-stage. Compose healthchecks:

- Postgres: `pg_isready`
- Backend: `GET /api/v1/health/ready` (includes DB)
- Frontend: HTTP check on port 3000

---

## 4. Environment Variables

Full tables: [`ProductionReadiness.md`](./ProductionReadiness.md) §3.

### 4.1 Backend (minimum)

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Async Postgres URL | Yes |
| `SECRET_KEY` | JWT / crypto secret | Yes (strong in prod) |
| `CORS_ORIGINS` | Allowed browser origins | Yes |
| `ENVIRONMENT` | `development` / `staging` / `production` | Yes |
| `LOG_FORMAT` | `json` or `text` | Prod: `json` |

### 4.2 Frontend

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | Yes |

---

## 5. Database Migrations

```bash
cd backend
alembic upgrade head
```

Create a revision:

```bash
alembic revision --autogenerate -m "description"
```

Do not rely on `Base.metadata.create_all` in production (`init_db` leaves schema to Alembic).

---

## 6. CI/CD Pipeline

### 6.1 GitHub Actions

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on push/PR:

1. Backend pytest
2. Frontend lint, `tsc --noEmit`, vitest

### 6.2 Suggested release flow

1. Merge to `develop` → CI green
2. Tag / promote to staging with production-like env
3. Confirm `/api/v1/health/ready` and smoke tests
4. Promote to production; keep rollback image tag

---

## 7. Monitoring

### 7.1 Health Checks

| Probe | Path |
|-------|------|
| Liveness | `/api/v1/health/live` |
| Readiness (DB) | `/api/v1/health/ready` → **503** if DB down |

### 7.2 Logging

Set `LOG_FORMAT=json` and ship stdout to your aggregator. Request correlation via `X-Request-Id`.

### 7.3 Alerts

Alert on readiness 503 rate, API 5xx, and Postgres disk/connection saturation.

---

## 8. Rollback Procedures

1. Redeploy previous known-good image tags for backend/frontend
2. If a migration is incompatible, run the matching Alembic downgrade only after backup restore planning
3. Verify `/api/v1/health/ready` after rollback

---

## 9. Troubleshooting

| Symptom | Check |
|---------|-------|
| Backend exits at start | Config validation errors (placeholder `SECRET_KEY`, `DEBUG=true` in prod, bad `LOG_FORMAT`) |
| Compose backend unhealthy | Postgres up? `curl localhost:8000/api/v1/health/ready` |
| CORS errors | `CORS_ORIGINS` includes the exact frontend origin |
| Auth 401s | `AUTH_ENABLED` and valid Bearer token |
| Frontend calls localhost | `NEXT_PUBLIC_API_URL` must be the public API `/api/v1` URL, then rebuild frontend |

---

## 10. Public deploy (Render) — shareable URL

Requires a free [Render](https://render.com) account. Login cannot be completed from this agent without your credentials.

### Steps

1. Push latest `main` (includes [`render.yaml`](../render.yaml))
2. Open https://dashboard.render.com/select-repo?type=blueprint
3. Connect GitHub → select **AI-QA-PLATFORM** → Apply Blueprint
4. After **aiqa-api** is live, copy its URL
5. Set **aiqa-web** env `NEXT_PUBLIC_API_URL` = `https://<aiqa-api-host>/api/v1`
6. Set **aiqa-api** env `CORS_ORIGINS` = `https://<aiqa-web-host>`
7. Redeploy both → share the **frontend** URL on LinkedIn

> Free web services may sleep when idle; first request can take 30–60s.
