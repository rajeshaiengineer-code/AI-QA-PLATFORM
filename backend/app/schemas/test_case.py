"""
Test Case Pydantic Schemas

Request/response models for AI Test Case Generator APIs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from app.models.enums import (
    Priority,
    TestCaseCategory,
    TestCaseSource,
    TestCaseStatus,
)
from app.schemas.base import BaseSchema, PaginatedResponse


class TestStepSchema(BaseSchema):
    """Single step within a test case."""

    action: str = Field(..., min_length=1)
    expected: Optional[str] = None


class GeneratedTestCaseDraft(BaseSchema):
    """Structured test case payload returned by the LLM (validated before persist)."""

    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: List[TestStepSchema] = Field(default_factory=list)
    expected_result: Optional[str] = None
    priority: Priority = Field(default=Priority.MEDIUM)
    category: TestCaseCategory
    tags: List[str] = Field(default_factory=list)
    is_automated: bool = False
    acceptance_criteria_index: Optional[int] = Field(
        None,
        ge=0,
        description="1-based index into the prompt's acceptance criteria list.",
    )


class TestCaseGenerateResult(BaseSchema):
    """Top-level LLM JSON envelope for test case generation."""

    test_cases: List[GeneratedTestCaseDraft] = Field(default_factory=list)
    summary: Optional[str] = None


class TestCaseGenerateRequest(BaseSchema):
    """Optional overrides when triggering test case generation."""

    logical_model: Optional[str] = Field(
        None,
        description="Logical model alias from ModelRegistry (default: 'default').",
        examples=["default", "fast", "balanced"],
    )
    categories: Optional[List[TestCaseCategory]] = Field(
        None,
        description=(
            "Optional subset of categories to generate. "
            "Defaults to all eight categories."
        ),
    )


class TestCaseResponse(BaseSchema):
    """Persisted test case returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440020",
                "story_id": "550e8400-e29b-41d4-a716-446655440000",
                "acceptance_criteria_id": None,
                "title": "Reset password with valid token",
                "description": "Happy-path password reset.",
                "preconditions": "User has a valid reset token",
                "steps": [
                    {"action": "Open reset link", "expected": "Form loads"},
                    {
                        "action": "Submit new password",
                        "expected": "Success message shown",
                    },
                ],
                "expected_result": "Password is updated and user can log in",
                "priority": "high",
                "is_automated": False,
                "order_index": 0,
                "category": "positive",
                "source": "ai",
                "status": "pending_review",
                "rejection_reason": None,
                "tags": ["positive", "auth"],
                "provider": "openai",
                "model": "gpt-4o-mini",
                "created_at": "2026-07-16T00:00:00Z",
                "updated_at": "2026-07-16T00:00:00Z",
                "is_deleted": False,
                "version": 1,
            }
        },
    )

    id: UUID
    story_id: UUID
    acceptance_criteria_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[Any]] = None
    expected_result: Optional[str] = None
    priority: Priority
    is_automated: bool = False
    order_index: int = 0
    category: Optional[TestCaseCategory] = None
    source: TestCaseSource = TestCaseSource.MANUAL
    status: TestCaseStatus = TestCaseStatus.DRAFT
    rejection_reason: Optional[str] = None
    tags: Optional[List[Any]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    is_deleted: bool = False
    version: int = 1

    @field_validator("category", mode="before")
    @classmethod
    def coerce_category(cls, value: Any) -> Any:
        if value is None or value == "":
            return None
        return value

    @field_validator("source", mode="before")
    @classmethod
    def coerce_source(cls, value: Any) -> Any:
        if value is None or value == "":
            return TestCaseSource.MANUAL
        return value

    @field_validator("status", mode="before")
    @classmethod
    def coerce_status(cls, value: Any) -> Any:
        if value is None or value == "":
            return TestCaseStatus.DRAFT
        return value


class TestCaseUpdate(BaseSchema):
    """Partial update payload for a test case under QA review."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[TestStepSchema]] = None
    expected_result: Optional[str] = None
    priority: Optional[Priority] = None
    is_automated: Optional[bool] = None
    category: Optional[TestCaseCategory] = None
    tags: Optional[List[str]] = None
    acceptance_criteria_id: Optional[UUID] = None
    change_reason: Optional[str] = Field(
        None,
        description="Optional note stored on the version snapshot.",
    )

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped


class TestCaseRejectRequest(BaseSchema):
    """Optional reason when rejecting a test case."""

    reason: Optional[str] = Field(
        None,
        max_length=2000,
        description="Why the test case was rejected.",
    )


class TestCaseApproveRequest(BaseSchema):
    """Optional note when approving a test case (currently unused payload)."""

    note: Optional[str] = Field(None, max_length=2000)


class TestCaseApproveAllResponse(BaseSchema):
    """Result of approving all pending test cases for a story."""

    story_id: UUID
    approved_count: int
    items: List[TestCaseResponse]
    workflow_advanced: bool = False
    workflow_run_id: Optional[UUID] = None
    message: Optional[str] = None


class TestCaseDecisionResponse(BaseSchema):
    """Result of an individual approve / reject decision."""

    test_case: TestCaseResponse
    workflow_advanced: bool = False
    workflow_run_id: Optional[UUID] = None
    message: Optional[str] = None


class TestCaseVersionResponse(BaseSchema):
    """Historical snapshot of a test case."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    id: UUID
    test_case_id: UUID
    version_number: int
    title: str
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[Any]] = None
    expected_result: Optional[str] = None
    priority: Priority
    is_automated: bool = False
    category: Optional[TestCaseCategory] = None
    tags: Optional[List[Any]] = None
    status: TestCaseStatus
    change_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    is_deleted: bool = False
    version: int = 1

    @field_validator("category", mode="before")
    @classmethod
    def coerce_category(cls, value: Any) -> Any:
        if value is None or value == "":
            return None
        return value

    @field_validator("status", mode="before")
    @classmethod
    def coerce_status(cls, value: Any) -> Any:
        if value is None or value == "":
            return TestCaseStatus.DRAFT
        return value


class TestCaseVersionListResponse(PaginatedResponse[TestCaseVersionResponse]):
    """Paginated version history for a test case."""

    pass


class TestCaseListResponse(PaginatedResponse[TestCaseResponse]):
    """Paginated list of test cases for a story."""

    pass


class TestCaseGenerateResponse(BaseSchema):
    """Result of an AI generation run."""

    story_id: UUID
    count: int
    items: List[TestCaseResponse]
    summary: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
