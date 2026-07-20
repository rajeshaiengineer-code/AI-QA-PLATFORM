"""
Application Factory Module

Creates and configures the FastAPI application instance.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging import logger
from app.core.exceptions import register_exception_handlers
from app.core.middleware import setup_middleware
from app.core.validation import validate_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Fail fast on unsafe / incomplete configuration
    validate_settings(settings)
    logger.info(
        "Configuration validated",
        extra_fields={"environment": settings.ENVIRONMENT},
    )

    # Startup
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION}",
        extra_fields={
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "log_format": settings.LOG_FORMAT,
        },
    )
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Register connector plugins (framework)
    from app.connectors.runtime import register_builtin_connectors

    register_builtin_connectors()
    logger.info("Connector plugins registered")

    # Register AI provider plugins (framework)
    from app.ai.runtime import register_builtin_ai_providers

    register_builtin_ai_providers()
    logger.info("AI provider plugins registered")

    # Register workflow agents (Story Analyzer, …)
    from app.orchestration.runtime import register_builtin_agents

    register_builtin_agents()
    logger.info("Workflow agents registered")

    # Optional: notify on WORKFLOW_COMPLETED / WORKFLOW_FAILED
    from app.orchestration.subscribers import register_notification_subscribers

    register_notification_subscribers()
    logger.info("Notification EventBus subscribers registered (if enabled)")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")
    
    # Close database connections
    await close_db()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    """
    Application factory function.
    
    Creates and configures a FastAPI application instance with:
    - Lifespan management
    - Exception handlers
    - Middleware
    - API routers
    
    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url=None,  # Disable default docs, we'll add custom ones
        redoc_url=None,
        openapi_url=None,
    )

    # Register exception handlers
    register_exception_handlers(app)
    logger.debug("Exception handlers registered")

    # Setup middleware
    setup_middleware(app)
    logger.debug("Middleware configured")

    # Register API routers
    register_routers(app)
    logger.debug("API routers registered")

    # Setup OpenAPI documentation
    setup_openapi(app)
    logger.debug("OpenAPI documentation configured")

    return app


def register_routers(app: FastAPI) -> None:
    """Register all API routers."""
    from app.api.v1.router import api_router
    
    app.include_router(
        api_router,
        prefix=settings.API_V1_PREFIX,
    )


def setup_openapi(app: FastAPI) -> None:
    """Configure OpenAPI documentation endpoints."""
    
    @app.get("/openapi.json", include_in_schema=False)
    async def get_openapi_schema():
        return get_openapi(
            title=settings.APP_NAME,
            version=settings.APP_VERSION,
            description=(
                f"{settings.APP_DESCRIPTION}\n\n"
                "## Modules\n"
                "- **Health** — liveness and readiness probes\n"
                "- **Authentication** — JWT register/login/refresh + RBAC (`AUTH_ENABLED`)\n"
                "- **Projects** — Project CRUD and dashboard stats\n"
                "- **Sprints** — Sprint CRUD with project relationships\n"
                "- **Stories** — Story CRUD with pagination, filters, and search\n"
                "- **AI** — Story Analyzer + Test Case Generator\n"
                "- **Test Cases** — Generated/manual test cases for stories\n"
                "- **Workflows** — Story pipeline orchestration (state machine)\n"
                "- **Executions** — Stub test execution engine (job + history + retry)\n"
                "- **Dashboard** — Org/project reporting: summary, trends, coverage, AI metrics\n"
                "- **Notifications** — Email (SMTP stub), Slack & Teams webhooks + history\n"
                "- **Jira Connector** — Jira Cloud connect, browse, and sync\n"
                "- **GitHub Connector** — Branch / commit / PR for automation artifacts\n\n"
                "Interactive docs: `/docs` (Swagger UI), `/redoc` (ReDoc)."
            ),
            routes=app.routes,
            tags=[
                {"name": "Health", "description": "Service health and readiness"},
                {
                    "name": "Authentication",
                    "description": (
                        "JWT authentication: register, login, refresh, and /me. "
                        "Organization memberships carry roles "
                        "(admin, qa, engineer, viewer). "
                        "Set AUTH_ENABLED=true to require Bearer tokens on "
                        "protected write routes; default is false for local/tests."
                    ),
                },
                {
                    "name": "Dashboard",
                    "description": (
                        "Reporting aggregates scoped by organization and/or project: "
                        "entity summary counts, execution time-series trends, "
                        "story/test-case coverage ratios, and AI pipeline metrics."
                    ),
                },
                {
                    "name": "Notifications",
                    "description": (
                        "Outbound notifications via email (SMTP stub / log), "
                        "Slack incoming webhook, or Microsoft Teams webhook. "
                        "Optional NotificationLog persistence and EventBus hook "
                        "on WORKFLOW_COMPLETED / WORKFLOW_FAILED."
                    ),
                },
                {
                    "name": "Projects",
                    "description": (
                        "Manage projects: create, list (filter/search/paginate), "
                        "get, update, soft-delete, and dashboard statistics."
                    ),
                },
                {
                    "name": "Sprints",
                    "description": (
                        "Manage sprints: create, list (filter/search/paginate), "
                        "get, update, and soft-delete. Sprints belong to a project."
                    ),
                },
                {
                    "name": "Stories",
                    "description": (
                        "Manage user stories: create, list (filter/search/paginate), "
                        "get, update, and soft-delete. "
                        "Search matches title and story key (`external_id`). "
                        "Includes AI analysis, test-case generation, and BDD endpoints."
                    ),
                },
                {
                    "name": "AI",
                    "description": (
                        "AI-assisted QA features built on the AI Framework. "
                        "Story Analyzer produces complexity, risk, and suggested "
                        "tests. Test Case Generator persists full TestCase rows "
                        "across eight QA categories. "
                        "BDD Generator produces Gherkin feature files from "
                        "approved (or draft) test cases."
                    ),
                },
                {
                    "name": "Test Cases",
                    "description": (
                        "List, generate, review, and approve test cases. "
                        "AI generation covers eight QA categories. "
                        "QA Approval supports edit, version history, "
                        "individual approve/reject, and approve-all."
                    ),
                },
                {
                    "name": "QA Approval",
                    "description": (
                        "QA review gate for generated test cases: "
                        "edit with version history, approve/reject individuals, "
                        "approve-all for a story, and optionally advance the "
                        "workflow from test_cases_generated to qa_approved."
                    ),
                },
                {
                    "name": "BDD",
                    "description": (
                        "Gherkin / Cucumber feature generation from test cases. "
                        "Supports Feature, Scenario, Scenario Outline, Examples, "
                        "and Tags. Persists BddFeature artifacts."
                    ),
                },
                {
                    "name": "Playwright",
                    "description": (
                        "Playwright TypeScript automation artifacts generated from "
                        "BDD and/or test cases. No browser execution in this module."
                    ),
                },
                {
                    "name": "Executions",
                    "description": (
                        "MVP execution engine using a stub/local runner (no real "
                        "browsers). Run by story, automation artifact, or job; "
                        "list history; get detail; retry failed executions; "
                        "AI failure analysis; create Jira bugs from failures. "
                        "Optionally emits ExecutionStarted / ExecutionCompleted "
                        "on a workflow run."
                    ),
                },
                {
                    "name": "Workflows",
                    "description": (
                        "Event-driven workflow engine: start, advance, QA approve, "
                        "retry, cancel, and inspect run status/logs."
                    ),
                },
                {
                    "name": "Jira Connector",
                    "description": (
                        "Jira Cloud integration via the Connector Framework. "
                        "Connect with email + API token, list projects/boards/sprints, "
                        "and sync issues into the platform."
                    ),
                },
                {
                    "name": "GitHub Connector",
                    "description": (
                        "GitHub integration via the Connector Framework. "
                        "Connect with PAT, create branches, commit artifact files, "
                        "open pull requests, and inspect status checks."
                    ),
                },
            ],
        )

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{settings.APP_NAME} - Swagger UI",
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc():
        return get_redoc_html(
            openapi_url="/openapi.json",
            title=f"{settings.APP_NAME} - ReDoc",
        )
