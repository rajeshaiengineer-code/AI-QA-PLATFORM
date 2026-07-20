"""
Sprint Pydantic Schemas

Request/response models for Sprint CRUD APIs.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.base import BaseSchema, PaginatedResponse


class SprintBase(BaseSchema):
    """Shared Sprint fields."""

    name: str = Field(..., min_length=1, max_length=255, examples=["Sprint 14"])
    goal: Optional[str] = Field(None, examples=["Ship checkout hardening"])
    external_id: Optional[str] = Field(None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped

    @model_validator(mode="after")
    def validate_date_range(self) -> "SprintBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class SprintCreate(SprintBase):
    """Payload for creating a sprint."""

    project_id: UUID = Field(..., description="Owning project ID")


class SprintUpdate(BaseSchema):
    """Payload for partial sprint update."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    goal: Optional[str] = None
    external_id: Optional[str] = Field(None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    project_id: Optional[UUID] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped

    @model_validator(mode="after")
    def validate_date_range(self) -> "SprintUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class SprintResponse(SprintBase):
    """Sprint API response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                "project_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "name": "Sprint 14",
                "goal": "Payments hardening",
                "external_id": None,
                "start_date": "2026-07-01",
                "end_date": "2026-07-14",
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
    project_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    is_deleted: bool = False
    version: int = 1


class SprintListResponse(PaginatedResponse[SprintResponse]):
    """Paginated list of sprints."""

    pass
