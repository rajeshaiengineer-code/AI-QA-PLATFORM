# AI QA Platform

Live demo product (agents, automation, frontend, backend).

**Share this repo (live demo):** https://github.com/rajeshaiengineer-code/AI-QA-PLATFORM

**Learning curriculum (separate repo):** https://github.com/rajeshaiengineer-code/qaautomation_academy

> Keep these repositories separate: this one is for product demos; the academy is for learning and code reference.

---

# AI QA Platform

An enterprise-grade AI-powered Quality Assurance Platform that automates the complete QA lifecycle.

---

## Overview

The AI QA Platform leverages artificial intelligence to transform software quality assurance by automating test case generation, execution, and reporting. From user story analysis to intelligent test automation, the platform reduces manual effort while improving test coverage and reliability.

### Key Features

- **AI-Powered Test Generation** - Automatically generate test cases from user stories
- **Unified Test Management** - Single platform for manual and automated testing
- **Intelligent Automation** - Self-healing test scripts with Playwright
- **Seamless Integrations** - Native integration with Jira and CI/CD pipelines
- **Real-time Analytics** - Comprehensive dashboards and quality metrics

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                    │
│                    Next.js + React + TypeScript                         │
│                         Tailwind CSS                                    │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  │ REST API
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                     │
│                             FastAPI                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │   API Layer  │  │   Services   │  │ Repositories │  │ AI Agents  │  │
│  │   (Routes)   │──│   (Logic)    │──│    (Data)    │  │ (LLM)      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                             DATABASE                                     │
│                           PostgreSQL                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
AI-QA-Platform/
│
├── backend/                 # FastAPI backend application
│   ├── app/
│   │   ├── api/            # API routes and endpoints
│   │   ├── core/           # Configuration and security
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic validation schemas
│   │   ├── services/       # Business logic layer
│   │   ├── repositories/   # Data access layer
│   │   ├── db/             # Database session management
│   │   ├── utils/          # Helper utilities
│   │   └── middleware/     # Request/response middleware
│   └── tests/              # Backend tests
│
├── frontend/               # Next.js frontend application
│   └── src/
│       ├── app/            # App Router pages
│       ├── components/     # Reusable UI components
│       ├── hooks/          # Custom React hooks
│       ├── services/       # API service functions
│       ├── lib/            # Utilities and configs
│       ├── store/          # State management
│       ├── types/          # TypeScript definitions
│       └── styles/         # Global styles
│
├── database/               # Database migrations and seeds
├── agents/                 # AI agent configurations
├── automation/             # Playwright tests and Cucumber features
├── prompts/                # AI prompt templates
├── scripts/                # Utility scripts
├── docker/                 # Docker configurations
├── docs/                   # Project documentation
│
├── docker-compose.yml      # Docker orchestration
├── PROJECT_CONTEXT.md      # Project reference document
└── README.md               # This file
```

---

## Technology Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| Next.js 16+ | React framework with App Router |
| TypeScript | Type safety |
| Tailwind CSS | Utility-first styling |
| Zustand | State management |

### Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | High-performance Python framework |
| SQLAlchemy | ORM for database operations |
| Alembic | Database migrations |
| Pydantic | Data validation |

### Database & Infrastructure
| Technology | Purpose |
|------------|---------|
| PostgreSQL | Primary database |
| Docker | Containerization |
| GitHub Actions | CI/CD pipelines |

### Testing & Automation
| Technology | Purpose |
|------------|---------|
| Playwright | E2E test automation |
| Cucumber | BDD test framework |
| Pytest | Backend testing |
| Jest | Frontend testing |

---

## Setup Instructions

### Prerequisites

- Node.js 20+
- Python 3.12+
- Docker & Docker Compose
- Git

### Quick Start (Docker)

```bash
# Clone the repository
git clone https://github.com/rajeshaiengineer-code/AI-QA-PLATFORM.git
cd AI-QA-PLATFORM

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Local Development

**Load sample data** (after Postgres is up and migrations applied):

```bash
# Stories / project / sprint
psql "$DATABASE_URL" -f database/seeds/001_sample_stories.sql
# Test cases, BDD, Playwright artifact, sample executions
psql "$DATABASE_URL" -f database/seeds/002_sample_pipeline.sql
```

See [docs/UserFlow.md](./docs/UserFlow.md) for the customer Jira → automation click-path, and [docs/UserGuide.md](./docs/UserGuide.md) for broader use cases.

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Access Points

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/api/v1/docs |

---

## Development Workflow

1. **Create Branch**: `git checkout -b feature/TICKET-description`
2. **Develop**: Follow coding standards in `PROJECT_CONTEXT.md`
3. **Test**: Write and run tests
4. **Commit**: Use conventional commits (`feat:`, `fix:`, `docs:`)
5. **PR**: Create pull request to `develop` branch
6. **Review**: Address feedback and merge

---

## Documentation

| Document | Description |
|----------|-------------|
| [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md) | Complete project reference |
| [docs/Architecture.md](./docs/Architecture.md) | System architecture + workflow engine |
| [docs/ConnectorArchitecture.md](./docs/ConnectorArchitecture.md) | Connector plugin framework |
| [docs/JiraIntegration.md](./docs/JiraIntegration.md) | Jira Cloud connector + sync |
| [docs/AIFramework.md](./docs/AIFramework.md) | AI provider abstraction (OpenAI / Gemini / Claude) |
| [docs/WorkflowEngine.md](./docs/WorkflowEngine.md) | Workflow engine runtime |
| [docs/API.md](./docs/API.md) | API documentation |
| [docs/Database.md](./docs/Database.md) | Database design |
| [docs/DevelopmentGuide.md](./docs/DevelopmentGuide.md) | Development setup |
| [docs/Roadmap.md](./docs/Roadmap.md) | Product roadmap |
| [docs/StoryAnalyzer.md](./docs/StoryAnalyzer.md) | AI Story Analyzer |
| [docs/TestCaseGenerator.md](./docs/TestCaseGenerator.md) | AI Test Case Generator |
| [docs/QAApproval.md](./docs/QAApproval.md) | QA Approval (review / versions / workflow gate) |
| [docs/BDDGenerator.md](./docs/BDDGenerator.md) | AI BDD / Gherkin Generator |
| [docs/PlaywrightGenerator.md](./docs/PlaywrightGenerator.md) | AI Playwright Generator |
| [docs/ExecutionEngine.md](./docs/ExecutionEngine.md) | Execution Engine (stub runner) |
| [docs/FailureAnalysis.md](./docs/FailureAnalysis.md) | AI Failure Analysis |
| [docs/JiraBugCreation.md](./docs/JiraBugCreation.md) | Jira Bug Creation from failures |
| [docs/GitHubIntegration.md](./docs/GitHubIntegration.md) | GitHub connector |
| [docs/Authentication.md](./docs/Authentication.md) | JWT auth + org RBAC |
| [docs/Notifications.md](./docs/Notifications.md) | Email / Slack / Teams notifications |
| [docs/UserGuide.md](./docs/UserGuide.md) | Use cases and step-by-step user flows |
| [docs/UserFlow.md](./docs/UserFlow.md) | Customer path: Jira connect → sync → automation |
| [docs/ProductionReadiness.md](./docs/ProductionReadiness.md) | CI, Docker, env validation, health, logging, pools |
| [docs/SecurityChecklist.md](./docs/SecurityChecklist.md) | Pre-production security review checklist |
| [docs/Deployment.md](./docs/Deployment.md) | Deploy, migrate, monitor, rollback |
| [frontend/docs/StoryManagement.md](./frontend/docs/StoryManagement.md) | Story Management UI (Milestone 6) |

---

## Roadmap

### Phase 1: Foundation ✓
- [x] Project structure
- [x] Backend setup (FastAPI)
- [x] Frontend setup (Next.js)
- [x] Docker configuration

### Phase 2: Core Features
- [x] User authentication (JWT + RBAC; `AUTH_ENABLED` default off)
- [ ] Project management
- [x] User story management (API + Frontend UI)
- [x] Test case management (QA approval API)

### Phase 3: AI & Automation
- [x] AI Framework (provider abstraction)
- [x] AI test case generation
- [x] QA approval (review API)
- [x] Jira Cloud integration (connect / browse / sync)
- [x] BDD / Gherkin generation
- [x] Playwright automation generation (artifacts; no browser run yet)
- [x] Test execution engine (stub/local runner; no real browsers)
- [x] AI failure analysis
- [x] Jira bug creation from failures
- [x] Notifications (email stub + Slack/Teams webhooks)
- [x] CI (GitHub Actions: backend pytest + frontend lint/tsc/test)

### Phase 4: Enterprise
- [ ] Advanced analytics
- [ ] Multi-tenant support
- [ ] Enterprise integrations
- [x] Production readiness (env validation, readiness/DB probes, Docker/CI, security checklist)

---

## Contributing

Please read `PROJECT_CONTEXT.md` for coding standards and contribution guidelines.

---

## License

MIT

---

## Contact

For questions or support, please open an issue on GitHub.
