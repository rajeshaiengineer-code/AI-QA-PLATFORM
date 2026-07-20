"""
Story Analysis Pydantic Schemas

Request/response models for AI Story Analyzer APIs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from app.models.enums import ComplexityLevel, RiskLevel
from app.schemas.base import BaseSchema


class SuggestedTestHint(BaseSchema):
    """Lightweight test suggestion produced by analysis (not a TestCase entity)."""

    title: str = Field(..., min_length=1, max_length=500)
    type: Optional[str] = Field(
        None,
        description="Hint category, e.g. functional, edge, negative, regression.",
    )
    rationale: Optional[str] = None


class StoryAnalysisResult(BaseSchema):
    """Structured analysis payload returned by the LLM (and validated before persist)."""

    complexity: ComplexityLevel = Field(default=ComplexityLevel.MEDIUM)
    risk: RiskLevel = Field(default=RiskLevel.MEDIUM)
    automation_candidate: bool = False
    dependencies: List[str] = Field(default_factory=list)
    suggested_tests: List[SuggestedTestHint] = Field(default_factory=list)
    summary: str = Field(..., min_length=1)
    notes: Optional[str] = None


class StoryAnalyzeRequest(BaseSchema):
    """Optional overrides when triggering analysis."""

    logical_model: Optional[str] = Field(
        None,
        description="Logical model alias from ModelRegistry (default: 'default').",
        examples=["default", "fast", "balanced"],
    )


class StoryAnalysisResponse(BaseSchema):
    """Persisted story analysis returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440010",
                "story_id": "550e8400-e29b-41d4-a716-446655440000",
                "complexity": "medium",
                "risk": "high",
                "automation_candidate": True,
                "dependencies": ["Auth service", "Email provider"],
                "suggested_tests": [
                    {
                        "title": "Reset password with valid token",
                        "type": "functional",
                        "rationale": "Happy path for core AC",
                    }
                ],
                "summary": "Password reset flow with email token validation.",
                "notes": "Ambiguous token expiry; clarify with product.",
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
    complexity: ComplexityLevel
    risk: RiskLevel
    automation_candidate: bool
    dependencies: Optional[List[Any]] = None
    suggested_tests: Optional[List[Any]] = None
    summary: str
    notes: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    is_deleted: bool = False
    version: int = 1
