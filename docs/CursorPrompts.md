# Cursor AI Prompts

## Document Information

| Field | Value |
|-------|-------|
| Purpose | AI-assisted development prompts |
| Last Updated | <!-- DATE --> |

---

## 1. Overview

This document contains effective prompts for using Cursor AI to develop the AI QA Platform.

---

## 2. Architecture Prompts

### 2.1 Component Creation

```
Create a new React component for [FEATURE] following the project's 
component structure. Include TypeScript types, proper styling with 
Tailwind CSS, and follow existing patterns in the codebase.
```

### 2.2 API Endpoint Creation

```
Create a new FastAPI endpoint for [FEATURE]. Follow the existing 
repository pattern, include proper Pydantic schemas, error handling, 
and add corresponding tests.
```

---

## 3. Feature Development Prompts

### 3.1 CRUD Operations

```
Implement complete CRUD operations for [ENTITY] including:
- Database model (SQLAlchemy)
- Pydantic schemas
- Repository layer
- Service layer
- API endpoints
- Frontend service
- React hooks
```

### 3.2 Integration

```
Integrate [SERVICE] with proper error handling, retry logic, 
and following the existing integration patterns in the codebase.
```

---

## 4. Testing Prompts

### 4.1 Unit Tests

```
Write unit tests for [COMPONENT/FUNCTION] with proper mocking, 
edge cases, and following the existing test patterns.
```

### 4.2 Integration Tests

```
Write integration tests for [FEATURE] covering the complete 
flow from API to database.
```

---

## 5. Refactoring Prompts

### 5.1 Code Improvement

```
Refactor [CODE] to improve readability, performance, and 
maintainability while maintaining existing functionality.
```

---

## 6. Documentation Prompts

### 6.1 Code Documentation

```
Add comprehensive documentation to [CODE] including JSDoc/docstrings, 
inline comments for complex logic, and usage examples.
```

---

## 7. Best Practices

- Always reference PROJECT_CONTEXT.md for coding standards
- Follow existing patterns in the codebase
- Include error handling in all implementations
- Write tests alongside feature development
