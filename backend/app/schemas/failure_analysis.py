"""
Failure Analysis Pydantic Schemas

Request/response models for AI Failure Analysis APIs.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from app.models.enums import FailureCategory
from app.schemas.base import BaseSchema


class FailureAnalysisResult(BaseSchema):
    """Structured analysis payload returned by the LLM (validated before persist)."""

    category: FailureCategory = Field(default=FailureCategory.UNKNOWN)
    is_flaky: bool = False
    is_product_bug: bool = False
    summary: str = Field(..., min_length=1)
    root_cause: str = Field(..., min_length=1)
    suggested_fix: str = Field(..., min_length=1)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    notes: Optional[str] = None


class FailureAnalyzeRequest(BaseSchema):
    """Optional evidence + model override when triggering failure analysis."""

    logical_model: Optional[str] = Field(
        None,
        description="Logical model alias from ModelRegistry (default: 'default').",
        examples=["default", "fast", "balanced"],
    )
    logs: Optional[str] = Field(
        None,
        description="Optional log text or stub path/URL.",
    )
    screenshot_url: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional screenshot path/URL (may be a stub).",
    )
    video_url: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional video path/URL (may be a stub).",
    )
    network_url: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional network HAR/log path/URL (may be a stub).",
    )
    trace_url: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional Playwright/trace path/URL (may be a stub).",
    )


class FailureAnalysisResponse(BaseSchema):
    """Persisted failure analysis returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440020",
                "execution_id": "550e8400-e29b-41d4-a716-446655440015",
                "category": "product_bug",
                "is_flaky": False,
                "is_product_bug": True,
                "summary": "Login button does not submit when password is empty.",
                "root_cause": "Client-side validation missing; API returns 500.",
                "suggested_fix": "Add required validation and return 400 from API.",
                "confidence": 0.82,
                "notes": None,
                "logs": "stub://logs/run-1.txt",
                "screenshot_url": "stub://screenshots/fail-1.png",
                "video_url": None,
                "network_url": None,
                "trace_url": None,
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
    execution_id: UUID
    category: FailureCategory
    is_flaky: bool
    is_product_bug: bool
    summary: str
    root_cause: str
    suggested_fix: str
    confidence: Optional[float] = None
    notes: Optional[str] = None
    logs: Optional[str] = None
    screenshot_url: Optional[str] = None
    video_url: Optional[str] = None
    network_url: Optional[str] = None
    trace_url: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    is_deleted: bool = False
    version: int = 1
