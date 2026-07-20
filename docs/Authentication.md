# Authentication & RBAC

## Document Information

| Field | Value |
|-------|-------|
| Milestone | Authentication + RBAC (Master Prompt Milestone 18) |
| Status | Implemented |
| Package | `backend/app/core/security.py`, `rbac.py`, `services/auth.py` |
| Last Updated | 2026-07-16 |

---

## 1. Overview

JWT-based authentication with organization membership roles.

| Concern | Implementation |
|---------|----------------|
| Access token | HS256 JWT, short-lived (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 30) |
| Refresh token | HS256 JWT, longer-lived (`REFRESH_TOKEN_EXPIRE_DAYS`, default 7) |
| Passwords | `passlib` + `bcrypt` |
| Toggle | `AUTH_ENABLED` (default **`false`**) — when false, write-route guards are no-ops so existing tests stay green |

Roles: **admin**, **qa**, **engineer**, **viewer**.

---

## 2. Data model

```
users
  email (unique), hashed_password, full_name, is_active, is_superuser
  + BaseEntity fields

organization_memberships
  user_id → users
  organization_id → organizations
  role ∈ {admin, qa, engineer, viewer}
  UNIQUE(user_id, organization_id)
```

Alembic revision: `auth_rbac_001` (`20260716_120000_users_and_memberships.py`).

```bash
cd backend && alembic upgrade head
```

---

## 3. API (`/api/v1/auth`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/register` | Public | Create user; optional org create (admin) or join (viewer) |
| POST | `/login` | Public | Email/password → token pair |
| POST | `/refresh` | Refresh JWT | New access + refresh pair |
| GET | `/me` | Bearer access | Profile + memberships |

Swagger tag: **Authentication**.

### Register body

```json
{
  "email": "qa@example.com",
  "password": "SecretPass1!",
  "full_name": "QA User",
  "organization_name": "Acme QA",
  "organization_slug": "acme-qa"
}
```

Or join an existing org with `"organization_id": "<uuid>"` (role = `viewer`).

### Token response

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": { "id": "...", "email": "...", "memberships": [] }
}
```

---

## 4. RBAC dependencies

| Dependency | Behavior when `AUTH_ENABLED=false` | When `true` |
|------------|-------------------------------------|-------------|
| `require_auth` | Allows anonymous | Requires valid access JWT |
| `require_write_access` | No-op | Requires admin / qa / engineer (or superuser) |
| `require_roles(...)` | No-op | Requires one of the listed roles |
| `require_org_role(min)` | No-op | Requires min role in `organization_id` |

Write ops currently guarded (no-op unless enabled):

- Story create / update / delete
- Project create / update / delete

Enable enforcement:

```bash
export AUTH_ENABLED=true
```

---

## 5. Key files

| Path | Role |
|------|------|
| `core/security.py` | Password hash + JWT create/decode |
| `core/rbac.py` | FastAPI auth/RBAC dependencies |
| `core/config.py` | `AUTH_ENABLED`, token TTLs |
| `models/user.py` | User entity |
| `models/organization_membership.py` | Membership + role |
| `services/auth.py` | Register / login / refresh / me |
| `api/v1/endpoints/auth.py` | HTTP routes |
| `tests/test_auth.py` | Auth flow + RBAC tests |

---

## 6. Frontend

Minimal login page: `/login` — email/password → stores tokens and redirects to dashboard.

Set `AUTH_ENABLED=true` on the API when using the UI against a secured backend.
