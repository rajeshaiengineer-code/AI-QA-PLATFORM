# Product Roadmap

## Document Information

| Field | Value |
|-------|-------|
| Version | 1.20 |
| Last Updated | 2026-07-21 |

---

## 1. Vision

Enterprise AI-powered QA platform: story → tests → automation → execution → insights.

---

## 2. Engineering Milestones

| Milestone | Status | Notes |
|-----------|--------|-------|
| 1–5 Foundation, DB, Workflow, Story CRUD API | ✅ Complete | Backend + docs |
| 6 Frontend Story Management | ✅ Complete | `/stories` dashboard |
| 7 Project + Sprint Management | ✅ Complete | CRUD APIs + UI + Project dashboard |
| **8 Connector Framework** | ✅ Complete | Plugin architecture |
| **9 Jira Integration** | ✅ Complete | Jira Cloud connector + sync APIs |
| **10 AI Framework** | ✅ Complete | Provider abstraction (OpenAI / Gemini / Claude) |
| **11 AI Story Analyzer** | ✅ Complete | REST analyze + persist + workflow agent |
| **12 AI Test Case Generator** | ✅ Complete | REST generate/list + persist + workflow agent |
| **13 QA Approval** | ✅ Complete | Review API + versions + workflow gate |
| **14 AI BDD Generator** | ✅ Complete | Gherkin from approved cases + agent |
| **15 AI Playwright Generator** | ✅ Complete | TS artifacts from BDD/cases + agent (no execution) |
| **16 GitHub Connector** | ✅ Complete | PAT auth + branch/commit/PR APIs + optional PR agent |
| **17 Execution Engine** | ✅ Complete | Stub + **local Playwright** runner (`runner=stub\|playwright`) + AutomationJob/Execution APIs + workflow events |
| **18 AI Failure Analysis** | ✅ Complete | AI root-cause + suggested fix; FailureAnalysis persist + agent |
| **19 Jira Bug Creation** | ✅ Complete | Jira create_issue + local Bug (external_id/metadata) + agent |
| **20 Dashboard & Reporting** | ✅ Complete | Summary / trends / coverage / AI metrics APIs + `/dashboard` UI |
| **21 Authentication + RBAC** | ✅ Complete | JWT + org memberships (admin/qa/engineer/viewer); `AUTH_ENABLED` default false |
| **22 Production Readiness** | ✅ Complete | CI, Docker healthchecks, env validation, readiness/DB 503, secrets + security docs |
| **23 Notifications** | ✅ Complete | Email (SMTP stub/log) + Slack/Teams webhooks + NotificationLog + EventBus hook (task: Milestone 19) |
| **24 Test Cases + Automation UI** | ✅ Complete | `/test-cases`, `/automation`, Integrations (Jira), seed pipeline, UserGuide |
---

## 3. Release Timeline

### Phase 1: Foundation

- [x] Project setup and architecture
- [x] PostgreSQL domain schema + Alembic
- [x] Workflow engine architecture
- [x] Workflow engine runtime (state machine, event bus, persistence)
- [x] Story CRUD API
- [x] Story Management UI
- [x] Connector Framework (plugin architecture)
- [x] Jira Cloud integration (connect / browse / sync)
- [x] Project / Sprint management
- [x] AI Framework (providers, prompts, model registry)
- [x] AI story analyzer
- [x] AI test case generator
- [x] QA approval (API)
- [x] Authentication (JWT + RBAC; see [`Authentication.md`](./Authentication.md))

### Phase 2: Core Features

- [x] Connector framework
- [x] Jira integration
- [x] AI Framework
- [x] AI story analyzer
- [x] AI test case generator (API)
- [x] QA approval workflow (API)
- [x] Test case management UI
- [x] Automation UI (BDD / Playwright / stub run)
- [x] Jira connect + sync UI

### Phase 3: Automation

- [x] BDD / Gherkin generation (API)
- [x] Playwright generation (API; artifacts only, no browser run)
- [x] GitHub connector (branch / commit / PR)
- [x] Test execution engine (stub + local Playwright CLI runner)
- [x] AI failure analysis (API + agent)
- [x] Jira bug creation from failures (API + agent)
- [x] Dashboard & reporting APIs (+ simple `/dashboard` UI)
- [x] CI (GitHub Actions) + production readiness docs
- [x] Notifications (email stub + Slack/Teams webhooks)
- [ ] Full CD promotion + BrowserStack / cloud runners
- [ ] Live SMTP (production email delivery)

### Phase 4: Enterprise

- [ ] Multi-tenant UX polish
- [ ] Advanced RBAC
- [ ] Audit logging

---

## 4. Dependencies

- Milestone 7 unblocks project/sprint selectors in Story forms
- Milestone 8–9 unblocks Jira import into Story Management
- Milestone 10 (AI Framework) unblocks LLM calls for agents
- Milestone 11 (Story Analyzer) unblocks test-case generation from analysis artifacts
- Milestone 12 (Test Case Generator) unblocks QA review / BDD from persisted `TestCase` rows
- Milestone 13 (QA Approval) unblocks BDD / automation stages after `qa_approved`
- Milestone 14 (BDD Generator) unblocks Playwright automation from Gherkin artifacts
- Milestone 15 (Playwright Generator) unblocks execution / PR stages from persisted TS artifacts
- Milestone 16 (GitHub Connector) unblocks `pull_request_created` workflow stage
- Milestone 17 (Execution Engine) unblocks failure analysis / reporting from persisted Executions
- Milestone 18 (Failure Analysis) unblocks defect filing from classified failures
- Milestone 19 (Jira Bug Creation) closes the loop to external tracker keys on local Bugs
- Milestone 20 (Dashboard & Reporting) surfaces execution + AI coverage metrics
- Milestone 21 (Authentication + RBAC) gates APIs with JWT when `AUTH_ENABLED=true`
- Milestone 22 (Production Readiness) CI + Docker/health + startup env validation + security checklist
- Milestone 23 (Notifications) email / Slack / Teams outbound + optional workflow EventBus hook
- Next: Full CD promotion + BrowserStack/cloud runners + live SMTP
- Local Playwright: `POST /api/v1/executions/run` with `"runner": "playwright"` (needs generated artifact + Node/`npx playwright`)
