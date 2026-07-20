"""
Core Module

Contains application configuration, database, logging, and utilities.
"""

from app.core.config import settings, get_settings
from app.core.database import (
    Base,
    engine,
    async_session_factory,
    get_async_session,
    get_session_context,
    init_db,
    close_db,
    check_db_connection,
)
from app.core.logging import logger, get_logger, set_request_id, get_request_id
from app.core.exceptions import (
    AppException,
    NotFoundException,
    BadRequestException,
    UnauthorizedException,
    ForbiddenException,
    ConflictException,
    DatabaseException,
    ServiceUnavailableException,
    register_exception_handlers,
)
from app.core.dependencies import (
    get_app_settings,
    get_db,
    get_pagination,
    get_sorting,
    PaginationParams,
    SortParams,
)
from app.core.middleware import setup_middleware

__all__ = [
    # Config
    "settings",
    "get_settings",
    # Database
    "Base",
    "engine",
    "async_session_factory",
    "get_async_session",
    "get_session_context",
    "init_db",
    "close_db",
    "check_db_connection",
    # Logging
    "logger",
    "get_logger",
    "set_request_id",
    "get_request_id",
    # Exceptions
    "AppException",
    "NotFoundException",
    "BadRequestException",
    "UnauthorizedException",
    "ForbiddenException",
    "ConflictException",
    "DatabaseException",
    "ServiceUnavailableException",
    "register_exception_handlers",
    # Dependencies
    "get_app_settings",
    "get_db",
    "get_pagination",
    "get_sorting",
    "PaginationParams",
    "SortParams",
    # Middleware
    "setup_middleware",
]
