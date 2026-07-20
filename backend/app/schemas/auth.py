"""Authentication and user / membership Pydantic schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.models.enums import OrganizationRole
from app.schemas.base import BaseSchema, TimestampSchema


class MembershipResponse(BaseSchema):
    """Organization membership summary for the current user."""

    id: UUID
    organization_id: UUID
    organization_name: Optional[str] = None
    organization_slug: Optional[str] = None
    role: OrganizationRole


class UserResponse(TimestampSchema):
    """Public user profile."""

    id: UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool = False
    memberships: List[MembershipResponse] = Field(default_factory=list)


class RegisterRequest(BaseSchema):
    """
    Register a new user.

    Optionally create a new organization (caller becomes admin) or join
    an existing organization as viewer.
    """

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    organization_id: Optional[UUID] = Field(
        None,
        description="Join an existing organization (role=viewer)",
    )
    organization_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Create a new organization; caller becomes admin",
    )
    organization_slug: Optional[str] = Field(
        None,
        max_length=100,
        description="Slug for the new organization (required with organization_name)",
    )

    @field_validator("password")
    @classmethod
    def password_not_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password cannot be blank")
        return value


class LoginRequest(BaseSchema):
    """Email / password login."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseSchema):
    """Exchange a refresh token for a new token pair."""

    refresh_token: str = Field(..., min_length=10)


class TokenResponse(BaseSchema):
    """JWT access + refresh token pair with user profile."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        ...,
        description="Access token lifetime in seconds",
    )
    user: UserResponse
