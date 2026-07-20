# Development Guide

## Document Information

| Field | Value |
|-------|-------|
| Version | 1.1 |
| Last Updated | 2026-07-16 |

---

## 1. Getting Started

### 1.1 Prerequisites

- Node.js 20+
- Python 3.12+
- Docker & Docker Compose
- Git

### 1.2 Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd AI-QA-Platform

# Start with Docker
docker-compose up -d
```

---

## 2. Development Environment

### 2.1 Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2.2 Frontend Development

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend runs at http://localhost:3000. Home redirects to **Story Management** (`/stories`).

Story UI docs: [`frontend/docs/StoryManagement.md`](../frontend/docs/StoryManagement.md)

```bash
# Frontend unit tests
cd frontend && npm test
```

**Note:** Creating a story requires a valid `project_id` in PostgreSQL until Project CRUD (Milestone 7). Optional: set `NEXT_PUBLIC_DEFAULT_PROJECT_ID` in `.env.local`.

---

## 3. Code Standards

### 3.1 Python Standards

<!-- Python coding standards -->

### 3.2 TypeScript Standards

<!-- TypeScript coding standards -->

---

## 4. Git Workflow

### 4.1 Branch Naming

<!-- Branch naming conventions -->

### 4.2 Commit Messages

<!-- Commit message format -->

### 4.3 Pull Request Process

<!-- PR process -->

---

## 5. Testing

### 5.1 Backend Testing

<!-- Backend testing guide -->

### 5.2 Frontend Testing

```bash
cd frontend
npm test
```

Vitest covers Story Zod schemas and `storyService` API calls (mocked).

---

## 6. Debugging

### 6.1 Common Issues

<!-- Common issues and solutions -->

### 6.2 Logging

<!-- Logging guidelines -->

---

## 7. Deployment

### 7.1 Local Deployment

<!-- Local deployment steps -->

### 7.2 Production Deployment

<!-- Production deployment steps -->
