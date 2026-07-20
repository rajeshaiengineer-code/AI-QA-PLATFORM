"""
Shared connector types and value objects.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConnectorCategory(str, Enum):
    """High-level connector family."""

    ISSUE_TRACKER = "issue_tracker"
    SOURCE_CONTROL = "source_control"
    AI_PROVIDER = "ai_provider"
    TEST_AUTOMATION = "test_automation"
    DEVICE_CLOUD = "device_cloud"
    CI_CD = "ci_cd"
    OTHER = "other"


class CredentialType(str, Enum):
    """Supported credential mechanisms."""

    API_KEY = "api_key"
    OAUTH = "oauth"
    USERNAME_PASSWORD = "username_password"
    PAT = "pat"
    BEARER_TOKEN = "bearer_token"


class HealthStatus(str, Enum):
    """Connector health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ConnectorEnvironment(str, Enum):
    """Deployment / configuration environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ConnectorMetadata(BaseModel):
    """Static descriptor for a connector plugin."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Unique connector key, e.g. 'jira'")
    display_name: str
    version: str = "0.1.0"
    category: ConnectorCategory = ConnectorCategory.OTHER
    description: str = ""
    provider: str = ""
    homepage: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    supported_credential_types: List[CredentialType] = Field(default_factory=list)
    config_schema_version: str = "1.0"


class ConnectorHealth(BaseModel):
    """Result of a connector health_check()."""

    status: HealthStatus = HealthStatus.UNKNOWN
    version: Optional[str] = None
    latency_ms: Optional[float] = None
    last_checked: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ConfigurationField(BaseModel):
    """Describes one configuration field for UI / validation."""

    name: str
    field_type: str = "string"
    required: bool = False
    description: str = ""
    default: Any = None
    secret: bool = False
    enum_values: Optional[List[str]] = None


class ConfigurationSchema(BaseModel):
    """Versioned configuration schema exposed by a connector."""

    schema_version: str = "1.0"
    title: str
    description: str = ""
    fields: List[ConfigurationField] = Field(default_factory=list)
