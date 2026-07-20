# Security Review Checklist

## Document Information

| Field | Value |
|-------|-------|
| Status | Living checklist (Milestone 22) |
| Last Updated | 2026-07-16 |

Use this before promoting a build to staging or production. Mark each item when verified.

---

## 1. Secrets & configuration

- [ ] No `.env`, credentials, or private keys committed (only `*.example` templates)
- [ ] Production `SECRET_KEY` is random, ≥32 characters, not an example placeholder
- [ ] AI provider keys (`AI_OPENAI_API_KEY`, `AI_GEMINI_API_KEY`, `AI_CLAUDE_API_KEY`) come from a secret store
- [ ] Jira / GitHub connector tokens are not in source control
- [ ] `DEBUG=false` and `ENVIRONMENT=production` in production
- [ ] Startup validation passes (`app.core.validation.validate_settings`)

---

## 2. Authentication & authorization

- [ ] `AUTH_ENABLED=true` in production
- [ ] JWT algorithm and expiry reviewed (`ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`)
- [ ] Org roles (admin / qa / engineer / viewer) applied on sensitive write routes
- [ ] Default admin credentials changed after first bootstrap
- [ ] Refresh tokens / logout behavior acceptable for the threat model

---

## 3. Network & HTTP

- [ ] `CORS_ORIGINS` limited to known frontends (no wildcard with credentials)
- [ ] TLS terminated in front of the API (reverse proxy / load balancer)
- [ ] Internal DB / Redis ports not exposed publicly
- [ ] Security headers considered at the edge (HSTS, etc.)

---

## 4. Data & database

- [ ] Postgres credentials rotated from compose defaults
- [ ] Connection pool sized under Postgres `max_connections` (see ProductionReadiness §7)
- [ ] Migrations applied via Alembic; no accidental `create_all` in production
- [ ] Backups / restore tested for the environment
- [ ] PII / secrets not written to application logs

---

## 5. Containers & runtime

- [ ] Images run as non-root (`appuser` / `nextjs`)
- [ ] Production containers do not mount source with `--reload`
- [ ] Health probes: liveness `/api/v1/health/live`, readiness `/api/v1/health/ready`
- [ ] Readiness returns **503** when the database is down
- [ ] Image scan / dependency audit scheduled (OS + npm + pip)

---

## 6. Logging & monitoring

- [ ] `LOG_FORMAT=json` in production
- [ ] Log aggregation receives request IDs (`X-Request-Id`)
- [ ] Alerts on readiness failures / elevated 5xx
- [ ] No secrets or full JWTs logged

---

## 7. Dependencies & supply chain

- [ ] CI green (backend pytest + frontend lint / tsc / test)
- [ ] Known CVEs reviewed for FastAPI / Next / Postgres client stacks
- [ ] Lockfiles committed (`package-lock.json`, pinned `requirements.txt`)

---

## 8. Application-specific

- [ ] AI prompts do not exfiltrate secrets from user content into third-party logs unexpectedly
- [ ] Connector operations respect least privilege (scoped GitHub PAT, Jira project access)
- [ ] File / artifact generation paths cannot write outside intended directories

---

## References

- [`ProductionReadiness.md`](./ProductionReadiness.md)
- [`Authentication.md`](./Authentication.md)
- [`Deployment.md`](./Deployment.md)
