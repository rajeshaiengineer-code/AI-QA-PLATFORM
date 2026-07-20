"""
Structured Logging Configuration Module

Provides JSON and text logging formats with request correlation.
"""

import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional
import json
import uuid

from app.core.config import settings

# Context variable for request correlation ID
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """Get current request correlation ID."""
    return request_id_ctx.get()


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set request correlation ID."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_ctx.set(request_id)
    return request_id


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if available
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Text log formatter for development."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        # Add request ID to message if available
        request_id = get_request_id()
        if request_id:
            record.msg = f"[{request_id[:8]}] {record.msg}"
        return super().format(record)


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter that includes context information."""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        extra = kwargs.get("extra", {})
        extra["extra_fields"] = kwargs.pop("extra_fields", {})
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging() -> None:
    """Configure application logging."""
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Set formatter based on configuration
    if settings.LOG_FORMAT.lower() == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())

    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DATABASE_ECHO else logging.WARNING
    )


def get_logger(name: str) -> ContextLogger:
    """
    Get a context-aware logger instance.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Processing request", extra_fields={"user_id": 123})
    """
    return ContextLogger(logging.getLogger(name), {})


# Initialize logging on module import
setup_logging()

# Default application logger
logger = get_logger("app")
