"""
Story Pydantic Schemas

Request/response models for Story CRUD APIs.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from app.models.enums import Priority, StoryStatus, StoryType
from app.schemas.base import BaseSchema, PaginatedResponse


class StoryBase(BaseSchema):
    """Shared Story fields."""

    title: str = Field(..., min_length=1, max_length=500, examples=["User can reset password"])
    description: Optional[str] = Field(None, examples=["As a user I want to reset my password..."])
    status: StoryStatus = Field(default=StoryStatus.DRAFT)
    story_type: StoryType = Field(default=StoryType.FEATURE)
    priority: Priority = Field(default=Priority.MEDIUM)
    story_points: Optional[int] = Field(None, ge=0, le=100)
    external_id: Optional[str] = Field(
        None,
        max_length=100,
        description="External tracker key (story key), e.g. Jira issue key.",
        examples=["PROJ-123"],
    )
    rank: Optional[int] = Field(None, ge=0)
    sprint_id: Optional[UUID] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped

    @field_validator("external_id")
    @classmethod
    def normalize_external_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class StoryCreate(StoryBase):
    """Payload for creating a story."""

    project_id: UUID = Field(..., description="Owning project ID")


class StoryUpdate(BaseSchema):
    """Payload for partial/full story update (all fields optional)."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[StoryStatus] = None
    story_type: Optional[StoryType] = None
    priority: Optional[Priority] = None
    story_points: Optional[int] = Field(None, ge=0, le=100)
    external_id: Optional[str] = Field(None, max_length=100)
    rank: Optional[int] = Field(None, ge=0)
    sprint_id: Optional[UUID] = None
    project_id: Optional[UUID] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped

    @field_validator("external_id")
    @classmethod
    def normalize_external_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class StoryResponse(StoryBase):
    """Story response returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "project_id": "550e8400-e29b-41d4-a716-446655440001",
                "sprint_id": None,
                "title": "User can reset password",
                "description": "As a user I want to reset my password via email.",
                "status": "draft",
                "story_type": "feature",
                "priority": "medium",
                "story_points": 3,
                "external_id": "PROJ-123",
                "rank": 1,
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
    project_id: UUID
    jira_issue_id: Optional[str] = None
    labels: Optional[list] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    external_updated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    is_deleted: bool = False
    version: int = 1


class StoryListResponse(PaginatedResponse[StoryResponse]):
    """Paginated list of stories."""

    pass


class StoryFilterParams(BaseSchema):
    """Query filters for listing stories."""

    status: Optional[StoryStatus] = None
    story_type: Optional[StoryType] = None
    priority: Optional[Priority] = None
    sprint_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    search: Optional[str] = Field(
        None,
        max_length=200,
        description="Search by story key (external_id) and/or title (case-insensitive).",
    )
