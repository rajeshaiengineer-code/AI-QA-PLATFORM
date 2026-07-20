"""
API V1 Router

Aggregates all v1 endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    bdd,
    dashboard,
    executions,
    github,
    health,
    jira,
    notifications,
    playwright,
    projects,
    sprints,
    stories,
    test_cases,
    workflows,
)

api_router = APIRouter()

# Health check endpoints
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

# Authentication + RBAC
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# Project management
api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"],
)

# Sprint management
api_router.include_router(
    sprints.router,
    prefix="/sprints",
    tags=["Sprints"],
)

# Story management
api_router.include_router(
    stories.router,
    prefix="/stories",
    tags=["Stories"],
)

# Test case QA review
api_router.include_router(
    test_cases.router,
    prefix="/test-cases",
    tags=["Test Cases"],
)

# BDD / Gherkin artifacts
api_router.include_router(
    bdd.router,
    prefix="/bdd",
    tags=["BDD"],
)

# Playwright automation artifacts
api_router.include_router(
    playwright.router,
    prefix="/playwright",
    tags=["Playwright"],
)

# Workflow engine
api_router.include_router(
    workflows.router,
    prefix="/workflows",
    tags=["Workflows"],
)

# Execution engine (stub runner)
api_router.include_router(
    executions.router,
    prefix="/executions",
    tags=["Executions"],
)

# Dashboard & reporting aggregates
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
)

# Notifications (email / Slack / Teams)
api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["Notifications"],
)

# Jira Cloud connector
api_router.include_router(
    jira.router,
    prefix="/connectors/jira",
    tags=["Jira Connector"],
)

# GitHub connector
api_router.include_router(
    github.router,
    prefix="/connectors/github",
    tags=["GitHub Connector"],
)