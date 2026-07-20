"""
Middleware Module

Custom middleware for request logging, timing, and correlation.
"""

import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import get_logger, set_request_id, request_id_ctx

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    
    Logs:
    - Request method and path
    - Response status code
    - Request duration
    - Request correlation ID
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # Set request correlation ID
        request_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(request_id)

        # Start timing
        start_time = time.perf_counter()

        # Get request info
        method = request.method
        path = request.url.path
        query_string = str(request.url.query) if request.url.query else ""
        client_ip = request.client.host if request.client else "unknown"

        # Log request
        logger.info(
            f"Request started: {method} {path}",
            extra_fields={
                "method": method,
                "path": path,
                "query": query_string,
                "client_ip": client_ip,
            },
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log error and re-raise
            duration = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed: {method} {path}",
                extra_fields={
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration, 2),
                    "error": str(exc),
                },
            )
            raise

        # Calculate duration
        duration = (time.perf_counter() - start_time) * 1000

        # Log response
        logger.info(
            f"Request completed: {method} {path} - {response.status_code}",
            extra_fields={
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
            },
        )

        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{round(duration, 2)}ms"

        return response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware for managing request context.
    
    Ensures context variables are properly set and cleaned up.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # Reset context at start of request
        request_id_ctx.set(None)
        
        try:
            response = await call_next(request)
            return response
        finally:
            # Clean up context
            request_id_ctx.set(None)


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""
    
    # Order matters: first added = outermost (last to execute on request)
    
    # 1. Request context (outermost)
    app.add_middleware(RequestContextMiddleware)
    
    # 2. Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # 3. CORS (needs to be added after other middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
