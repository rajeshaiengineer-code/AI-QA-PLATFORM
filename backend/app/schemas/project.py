"""
Project Pydantic Schemas

Request/response models for Project CRUD APIs.
"""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from app.schemas.base import BaseSchema, PaginatedResponse


class ProjectBase(BaseSchema):
    """Shared Project fields."""

    name: str = Field(..., min_length=1, max_length=255, examples=["Payments Platform"])
    key: str = Field(
        ...,
        min_length=2,
        max_length=20,
        examples=["PAY"],
        description="Short project key (unique within organization).",
    )
    description: Optional[str] = Field(None, examples=["Core payment rails and checkout"])
    external_id: Optional[str] = Field(None, max_length=100)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        stripped = value.strip().upper()
        if len(stripped) < 2:
            raise ValueError("key must be at least 2 characters")
        if not stripped.replace("-", "").replace("_", "").isalnum():
            raise ValueError("key must be alphanumeric (hyphen/underscore allowed)")
        return stripped

    @field_validator("external_id")
    @classmethod
    def normalize_external_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProjectCreate(ProjectBase):
    """Payload for creating a project."""

    organization_id: UUID = Field(..., description="Owning organization ID")


class ProjectUpdate(BaseSchema):
    """Payload for partial project update."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    key: Optional[str] = Field(None, min_length=2, max_length=20)
    description: Optional[str] = None
    external_id: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    organization_id: Optional[UUID] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip().upper()
        if len(stripped) < 2:
            raise ValueError("key must be at least 2 characters")
        if not stripped.replace("-", "").replace("_", "").isalnum():
            raise ValueError("key must be alphanumeric (hyphen/underscore allowed)")
        return stripped


class ProjectResponse(ProjectBase):
    """Project API response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "organization_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "name": "Payments Platform",
                "key": "PAY",
                "description": "Core payment rails",
                "external_id": None,
                "is_active": True,
                "created_at": "2026-07-16T00:00:00Z",
                "updated_at": "2026-07-16T00:00:00Z",
                "created_by": None,
                "updated_by": None,
                "is_deleted": False,
                "version": 1,
            }
        },
    )

    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    is_deleted: bool = False
    version: int = 1


class ProjectListResponse(PaginatedResponse[ProjectResponse]):
    """Paginated list of projects."""

    pass


class ProjectDashboardStats(BaseSchema):
    """Aggregate stats for a project dashboard."""

    project_id: UUID
    story_total: int = 0
    story_by_status: Dict[str, int] = Field(default_factory=dict)
    sprint_total: int = 0
    active_sprint_total: int = 0
