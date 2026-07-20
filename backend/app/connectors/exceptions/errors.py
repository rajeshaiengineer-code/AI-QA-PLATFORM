"""
Connector Framework Exceptions
"""

from typing import Any, Dict, Optional


class ConnectorError(Exception):
    """Base error for the connector framework."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "CONNECTOR_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class ConnectorNotFoundError(ConnectorError):
    """Requested connector is not registered."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Connector '{name}' is not registered",
            code="CONNECTOR_NOT_FOUND",
            details={"name": name},
        )


class ConnectorDisabledError(ConnectorError):
    """Connector exists but is disabled."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Connector '{name}' is disabled",
            code="CONNECTOR_DISABLED",
            details={"name": name},
        )


class ConnectorAlreadyRegisteredError(ConnectorError):
    """Duplicate registration attempt."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Connector '{name}' is already registered",
            code="CONNECTOR_ALREADY_REGISTERED",
            details={"name": name},
        )


class ConnectorConfigurationError(ConnectorError):
    """Invalid or incomplete connector configuration."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message,
            code="CONNECTOR_CONFIGURATION_ERROR",
            details=details,
        )


class ConnectorCredentialError(ConnectorError):
    """Missing, invalid, or unsupported credentials."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message,
            code="CONNECTOR_CREDENTIAL_ERROR",
            details=details,
        )


class ConnectorConnectionError(ConnectorError):
    """Failure establishing or closing a connection."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message,
            code="CONNECTOR_CONNECTION_ERROR",
            details=details,
        )


class ConnectorHealthCheckError(ConnectorError):
    """Health check could not be completed."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message,
            code="CONNECTOR_HEALTH_CHECK_ERROR",
            details=details,
        )
