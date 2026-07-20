# Notifications

## Document Information

| Field | Value |
|-------|-------|
| Milestone | Notifications (Milestone 19) |
| Roadmap row | 23 (19 was already Jira Bug Creation) |
| Status | **Complete** |
| Last Updated | 2026-07-16 |
| Package | `backend/app/services/notifications/` |

---

## 1. Purpose

Outbound multi-channel notifications for QA ops:

- **Email** — SMTP stub that logs (no real SMTP connection)
- **Slack** — incoming webhook via `httpx`
- **Teams** — incoming webhook via `httpx`
- Optional **`NotificationLog`** persistence
- Optional **EventBus** subscriber on `WORKFLOW_COMPLETED` / `WORKFLOW_FAILED`

---

## 2. Clean Architecture

```
schema (notification.py)
  → repository (notification.py)
    → service (notifications/service.py + channels/*)
      → endpoint (notifications.py)
```

| Layer | Module |
|-------|--------|
| Schema | `app/schemas/notification.py` |
| Model | `app/models/notification_log.py` |
| Repository | `app/repositories/notification.py` |
| Channels | `app/services/notifications/channels/{email,slack,teams}.py` |
| Service | `app/services/notifications/service.py` |
| API | `app/api/v1/endpoints/notifications.py` |
| EventBus hook | `app/orchestration/subscribers/notifications.py` |

---

## 3. Configuration

| Setting | Default | Notes |
|---------|---------|-------|
| `SMTP_HOST` | unset | Logged in stub; no live SMTP |
| `SMTP_PORT` | `587` | Informational for stub |
| `SMTP_USER` / `SMTP_PASSWORD` | unset | Reserved for future real SMTP |
| `SMTP_FROM` | `noreply@ai-qa-platform.local` | From address in log line |
| `SMTP_USE_TLS` | `true` | Reserved |
| `SLACK_WEBHOOK_URL` | unset | Required for Slack channel |
| `TEAMS_WEBHOOK_URL` | unset | Required for Teams channel |
| `NOTIFICATIONS_PERSIST` | `true` | Write `NotificationLog` on send |
| `NOTIFICATIONS_WORKFLOW_HOOK` | `true` | Subscribe to workflow terminal events |
| `NOTIFICATIONS_DEFAULT_RECIPIENT` | unset | Required for EventBus auto-notify |
| `NOTIFICATIONS_DEFAULT_CHANNEL` | `email` | Channel for workflow hook |

---

## 4. API

Swagger tag: **Notifications**. Base path: `/api/v1/notifications`.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/notifications/send` | Send on `email` \| `slack` \| `teams` |
| `GET` | `/api/v1/notifications` | Paginated history |

### Send body

```json
{
  "channel": "email",
  "recipient": "qa@example.com",
  "subject": "Suite failed",
  "body": "Execution XYZ failed",
  "persist": true,
  "metadata": {"source": "manual"}
}
```

- `subject` is **required** for `email`
- `persist` overrides `NOTIFICATIONS_PERSIST` when set
- Write route uses `require_write_access` (no-op when `AUTH_ENABLED=false`)

### History query params

`channel`, `status`, `organization_id`, `project_id`, `story_id`, `page`, `page_size`

---

## 5. EventBus hook

On app startup, when `NOTIFICATIONS_WORKFLOW_HOOK=true`:

- Subscribe to `WORKFLOW_COMPLETED` and `WORKFLOW_FAILED`
- If `NOTIFICATIONS_DEFAULT_RECIPIENT` is set, send via the default channel
- Skip quietly when recipient is unset (safe for local/tests)

---

## 6. Tests

`backend/tests/test_notifications.py`

- Email channel logs without SMTP
- Slack / Teams mock `httpx.AsyncClient.post`
- Send + list history; `persist=false`
- `AUTH_ENABLED=false` send remains open
- EventBus lifecycle handler with test session factory
