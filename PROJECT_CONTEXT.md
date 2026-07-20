# PROJECT CONTEXT

> **This is the permanent reference document for the AI QA Platform repository.**
> All developers and AI assistants should follow the guidelines defined here.

---

## 1. Project Vision

The AI QA Platform aims to revolutionize software quality assurance by leveraging artificial intelligence to automate the complete QA lifecycle. From user story analysis to test case generation, execution, and reporting — the platform will reduce manual effort while improving test coverage and reliability.

### Core Value Proposition

- **AI-Powered Test Generation**: Automatically generate comprehensive test cases from user stories
- **Intelligent Automation**: Self-healing test scripts that adapt to UI changes
- **Unified Platform**: Single platform for manual and automated testing
- **Seamless Integration**: Native integration with Jira, CI/CD pipelines, and development tools

---

## 2. Product Goal

Build an enterprise-grade QA platform that:

1. Reduces test case creation time by 70%
2. Increases test coverage by 50%
3. Decreases test maintenance effort by 60%
4. Provides real-time quality insights and analytics

---

## 3. Target Users

| User Role | Description | Primary Needs |
|-----------|-------------|---------------|
| QA Lead | Manages QA team and strategy | Dashboards, reporting, team management |
| QA Engineer | Creates and executes tests | Test creation, automation, execution |
| Developer | Writes and fixes code | Integration, test results, quick feedback |
| Product Manager | Defines requirements | Quality metrics, release readiness |
| DevOps Engineer | Manages CI/CD | Pipeline integration, automation triggers |

---

## 4. Architecture Principles

### 4.1 Clean Architecture

The project follows Clean Architecture principles with clear separation of concerns:

```
┌─────────────────────────────────────────────┐
│              Presentation Layer              │
│         (API Routes, Controllers)            │
├─────────────────────────────────────────────┤
│              Application Layer               │
│           (Services, Use Cases)              │
├─────────────────────────────────────────────┤
│                Domain Layer                  │
│         (Entities, Business Logic)           │
├─────────────────────────────────────────────┤
│             Infrastructure Layer             │
│    (Database, External Services, APIs)       │
└─────────────────────────────────────────────┘
```

### 4.2 Design Patterns

- **Repository Pattern**: Data access abstraction
- **Service Pattern**: Business logic encapsulation
- **Factory Pattern**: Object creation
- **Observer Pattern**: Event handling
- **Strategy Pattern**: Algorithm selection

### 4.3 API Design

- RESTful API design
- Versioned endpoints (`/api/v1/`)
- Consistent response format
- Proper HTTP status codes
- Comprehensive error handling

---

## 5. Coding Standards

### 5.1 Python (Backend)

```python
# Use type hints
def get_user(user_id: int) -> User:
    pass

# Use docstrings
def create_test_case(story_id: str, data: CreateTestCaseRequest) -> TestCase:
    """
    Create a new test case for a story.
    
    Args:
        story_id: The ID of the parent story
        data: Test case creation data
        
    Returns:
        The created test case
        
    Raises:
        NotFoundException: If story not found
    """
    pass

# Naming: snake_case for functions/variables
# Naming: PascalCase for classes
# Max line length: 100 characters
# Use f-strings for formatting
```

### 5.2 TypeScript (Frontend)

```typescript
// Use explicit types
interface Props {
  title: string;
  onSubmit: (data: FormData) => void;
}

// Use functional components with TypeScript
const Component: React.FC<Props> = ({ title, onSubmit }) => {
  // Component logic
};

// Naming: camelCase for functions/variables
// Naming: PascalCase for components/interfaces/types
// Use const for immutable values
// Prefer arrow functions
```

### 5.3 General Rules

- No magic numbers or strings (use constants)
- Maximum function length: 50 lines
- Maximum file length: 400 lines
- Single responsibility per function/class
- Meaningful variable and function names
- No commented-out code in commits

---

## 6. Folder Responsibilities

### 6.1 Root Folders

| Folder | Responsibility |
|--------|----------------|
| `backend/` | FastAPI application, API, business logic |
| `frontend/` | Next.js application, UI components |
| `database/` | Migrations, seeds, SQL scripts |
| `agents/` | AI agent configurations and workflows |
| `automation/` | Playwright tests, Cucumber features |
| `prompts/` | AI prompt templates and configurations |
| `scripts/` | Utility and deployment scripts |
| `docker/` | Docker configurations and compose files |
| `docs/` | Project documentation |

### 6.2 Backend Structure

| Folder | Responsibility |
|--------|----------------|
| `api/` | HTTP routes and request handling |
| `core/` | Configuration, security, constants |
| `models/` | SQLAlchemy ORM models |
| `schemas/` | Pydantic validation schemas |
| `services/` | Business logic and use cases |
| `repositories/` | Data access layer |
| `db/` | Database session management |
| `utils/` | Helper utilities |
| `middleware/` | Request/response middleware |

### 6.3 Frontend Structure

| Folder | Responsibility |
|--------|----------------|
| `app/` | Next.js App Router pages |
| `components/` | Reusable UI components |
| `hooks/` | Custom React hooks |
| `services/` | API service functions |
| `lib/` | Utilities and configurations |
| `store/` | Global state management |
| `types/` | TypeScript type definitions |
| `styles/` | Global styles and themes |

---

## 7. Tech Stack

### 7.1 Frontend

| Technology | Purpose |
|------------|---------|
| Next.js 16+ | React framework |
| React 19+ | UI library |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| Zustand | State management |
| Axios | HTTP client |
| React Hook Form | Form handling |
| Zod | Schema validation |

### 7.2 Backend

| Technology | Purpose |
|------------|---------|
| FastAPI | Web framework |
| SQLAlchemy | ORM |
| Alembic | Migrations |
| Pydantic | Data validation |
| Python-Jose | JWT handling |
| Passlib | Password hashing |

### 7.3 Database

| Technology | Purpose |
|------------|---------|
| PostgreSQL 16 | Primary database |
| Redis | Caching (future) |

### 7.4 Testing & Automation

| Technology | Purpose |
|------------|---------|
| Pytest | Backend testing |
| Jest/Vitest | Frontend testing |
| Playwright | E2E testing |
| Cucumber | BDD testing |

### 7.5 Infrastructure

| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Docker Compose | Local orchestration |
| GitHub Actions | CI/CD |
| AWS | Cloud hosting (future) |

---

## 8. Naming Conventions

### 8.1 Files and Folders

| Type | Convention | Example |
|------|------------|---------|
| React Component | PascalCase | `UserProfile.tsx` |
| Hook | camelCase with 'use' prefix | `useAuth.ts` |
| Service | camelCase with '.service' suffix | `auth.service.ts` |
| Store | camelCase with '.store' suffix | `auth.store.ts` |
| Type file | camelCase | `auth.ts` |
| Python module | snake_case | `user_service.py` |
| Test file | prefix/suffix with 'test' | `test_user.py`, `User.test.tsx` |

### 8.2 Variables and Functions

| Language | Convention | Example |
|----------|------------|---------|
| Python variables | snake_case | `user_name` |
| Python functions | snake_case | `get_user_by_id()` |
| Python classes | PascalCase | `UserService` |
| TS/JS variables | camelCase | `userName` |
| TS/JS functions | camelCase | `getUserById()` |
| TS/JS classes | PascalCase | `UserService` |
| Constants | SCREAMING_SNAKE_CASE | `API_BASE_URL` |

### 8.3 Database

| Type | Convention | Example |
|------|------------|---------|
| Tables | snake_case, plural | `users`, `test_cases` |
| Columns | snake_case | `created_at`, `user_id` |
| Primary keys | `id` | `id` |
| Foreign keys | singular_table_id | `user_id`, `project_id` |
| Indexes | idx_table_column | `idx_users_email` |

---

## 9. Git Workflow

### 9.1 Branch Strategy

```
main (production)
  └── develop (integration)
        ├── feature/TICKET-123-feature-name
        ├── bugfix/TICKET-456-bug-description
        ├── hotfix/TICKET-789-critical-fix
        └── release/v1.0.0
```

### 9.2 Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/TICKET-description` | `feature/QA-123-user-authentication` |
| Bugfix | `bugfix/TICKET-description` | `bugfix/QA-456-fix-login-error` |
| Hotfix | `hotfix/TICKET-description` | `hotfix/QA-789-security-patch` |
| Release | `release/vX.Y.Z` | `release/v1.0.0` |

### 9.3 Commit Message Style

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```
feat(auth): add user registration endpoint
fix(ui): resolve button alignment issue on mobile
docs(api): update authentication documentation
refactor(services): extract common validation logic
```

---

## 10. SOLID Principles

### Single Responsibility

Each class/module should have only one reason to change.

### Open/Closed

Open for extension, closed for modification.

### Liskov Substitution

Subtypes must be substitutable for their base types.

### Interface Segregation

Many specific interfaces are better than one general interface.

### Dependency Inversion

Depend on abstractions, not concretions.

---

## 11. Error Handling Strategy

### 11.1 Backend

```python
# Custom exception classes
class AppException(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code

class NotFoundException(AppException):
    def __init__(self, resource: str, id: str):
        super().__init__(
            message=f"{resource} with id {id} not found",
            code="NOT_FOUND",
            status_code=404
        )
```

### 11.2 Frontend

```typescript
// Centralized error handling
try {
  await apiCall();
} catch (error) {
  if (error instanceof ApiError) {
    handleApiError(error);
  } else {
    handleUnexpectedError(error);
  }
}
```

---

## 12. Logging Strategy

### 12.1 Log Levels

| Level | Usage |
|-------|-------|
| ERROR | Application errors requiring attention |
| WARN | Potential issues or degraded behavior |
| INFO | Significant business events |
| DEBUG | Detailed debugging information |

### 12.2 Log Format

```
{timestamp} | {level} | {service} | {correlation_id} | {message} | {context}
```

---

## 13. Documentation Rules

- All public functions must have docstrings/JSDoc
- Complex logic must have inline comments
- API endpoints must be documented in OpenAPI
- Architecture decisions must be documented in ADRs
- Keep documentation up-to-date with code changes

---

## 14. Cursor AI Rules

When using Cursor AI for development:

1. **Always reference this document** for coding standards
2. **Follow existing patterns** in the codebase
3. **Include error handling** in all implementations
4. **Write tests** alongside feature development
5. **Use TypeScript types** explicitly
6. **Follow the folder structure** defined here
7. **Use meaningful names** for variables and functions
8. **Keep functions small** and focused
9. **Document complex logic** with comments
10. **Validate inputs** at system boundaries

---

## 15. AI Assistant Rules

When AI assistants work on this project:

1. Read PROJECT_CONTEXT.md before making changes
2. Follow the established architecture patterns
3. Maintain consistency with existing code style
4. Create appropriate tests for new features
5. Update documentation when making changes
6. Use the defined naming conventions
7. Implement proper error handling
8. Add logging for significant operations
9. Keep commits atomic and well-described
10. Ask for clarification when requirements are unclear

---

## 16. Development Workflow

### 16.1 Feature Development

1. Create branch from `develop`
2. Implement feature following standards
3. Write tests (unit, integration)
4. Update documentation if needed
5. Create pull request
6. Address review feedback
7. Merge after approval

### 16.2 Code Review Checklist

- [ ] Follows coding standards
- [ ] Has appropriate tests
- [ ] Error handling is implemented
- [ ] No security vulnerabilities
- [ ] Performance is acceptable
- [ ] Documentation is updated
- [ ] No breaking changes (or documented)

---

## 17. Future Modules

| Module | Description | Priority |
|--------|-------------|----------|
| AI Test Generator | Generate test cases from stories | High |
| Jira Integration | Sync stories from Jira | High |
| Playwright Automation | Execute automated tests | High |
| Reporting Dashboard | Test metrics and analytics | Medium |
| CI/CD Integration | Pipeline triggers and results | Medium |
| Self-Healing Tests | Auto-fix broken selectors | Low |
| Mobile Testing | iOS/Android test support | Low |
| Performance Testing | Load and stress testing | Low |

---

## 18. Contact

For questions about this document or the project, contact the project maintainers.

---

**Last Updated:** <!-- DATE -->  
**Version:** 1.0.0
