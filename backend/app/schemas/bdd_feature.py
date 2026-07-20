"""
BDD Feature Pydantic Schemas

Request/response models for AI BDD Generator APIs.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.base import BaseSchema, PaginatedResponse


ScenarioType = Literal["scenario", "scenario_outline"]


class GherkinStepDraft(BaseSchema):
    """Single Gherkin step (Given / When / Then / And / But)."""

    keyword: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)

    @field_validator("keyword")
    @classmethod
    def normalize_keyword(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("keyword must not be blank")
        # Preserve common casing; capitalize first letter for Gherkin keywords
        lower = cleaned.lower()
        mapping = {
            "given": "Given",
            "when": "When",
            "then": "Then",
            "and": "And",
            "but": "But",
            "*": "*",
        }
        return mapping.get(lower, cleaned[0].upper() + cleaned[1:])


class GherkinExamplesDraft(BaseSchema):
    """Examples table for a Scenario Outline."""

    name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_table(self) -> "GherkinExamplesDraft":
        if not self.headers:
            raise ValueError("examples.headers must not be empty")
        width = len(self.headers)
        for idx, row in enumerate(self.rows):
            if len(row) != width:
                raise ValueError(
                    f"examples row {idx} has {len(row)} cells; expected {width}"
                )
        return self


class GherkinScenarioDraft(BaseSchema):
    """Scenario or Scenario Outline with optional Examples."""

    type: ScenarioType = "scenario"
    name: str = Field(..., min_length=1, max_length=500)
    tags: List[str] = Field(default_factory=list)
    steps: List[GherkinStepDraft] = Field(default_factory=list)
    examples: Optional[GherkinExamplesDraft] = None

    @model_validator(mode="after")
    def outline_requires_examples(self) -> "GherkinScenarioDraft":
        if self.type == "scenario_outline" and self.examples is None:
            raise ValueError("scenario_outline requires examples")
        if self.type == "scenario" and self.examples is not None:
            # Allow but ignore — or keep for flexibility; keep as-is
            pass
        if not self.steps:
            raise ValueError("scenario must include at least one step")
        return self


class GherkinFeatureDraft(BaseSchema):
    """Structured Feature envelope returned by the LLM."""

    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    scenarios: List[GherkinScenarioDraft] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_scenarios(self) -> "GherkinFeatureDraft":
        if not self.scenarios:
            raise ValueError("feature must include at least one scenario")
        return self


class BddGenerateResult(BaseSchema):
    """Top-level LLM JSON envelope for BDD generation."""

    feature: GherkinFeatureDraft
    summary: Optional[str] = None
    gherkin_content: Optional[str] = Field(
        None,
        description="Optional pre-rendered Gherkin; service may regenerate from feature.",
    )


class BddGenerateRequest(BaseSchema):
    """Optional overrides when triggering BDD generation."""

    logical_model: Optional[str] = Field(
        None,
        description="Logical model alias from ModelRegistry (default: 'default').",
        examples=["default", "fast", "balanced"],
    )
    include_drafts: bool = Field(
        False,
        description=(
            "When false (default), only approved test cases are used. "
            "When true, also include draft and pending_review cases "
            "(rejected cases are never included)."
        ),
    )


class BddFeatureResponse(BaseSchema):
    """Persisted BDD feature returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440030",
                "story_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Password reset",
                "description": "As a user I can reset my password",
                "gherkin_content": (
                    "@auth\nFeature: Password reset\n"
                    "  Scenario: Reset with valid token\n"
                    "    Given a valid reset token\n"
                    "    When the user submits a new password\n"
                    "    Then the password is updated\n"
                ),
                "tags": ["@auth"],
                "scenarios": [
                    {
                        "type": "scenario",
                        "name": "Reset with valid token",
                        "tags": ["@positive"],
                        "steps": [
                            {"keyword": "Given", "text": "a valid reset token"},
                            {
                                "keyword": "When",
                                "text": "the user submits a new password",
                            },
                            {"keyword": "Then", "text": "the password is updated"},
                        ],
                        "examples": None,
                    }
                ],
                "source_test_case_ids": ["550e8400-e29b-41d4-a716-446655440020"],
                "include_drafts": False,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "summary": "Happy-path and outline coverage for password reset.",
                "created_at": "2026-07-16T00:00:00Z",
                "updated_at": "2026-07-16T00:00:00Z",
                "is_deleted": False,
                "version": 1,
            }
        },
    )

    id: UUID
    story_id: UUID
    name: str
    description: Optional[str] = None
    gherkin_content: str
    tags: Optional[List[Any]] = None
    scenarios: Optional[List[Any]] = None
    source_test_case_ids: Optional[List[Any]] = None
    include_drafts: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None
    summary: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    is_deleted: bool = False
    version: int = 1


class BddFeatureListResponse(PaginatedResponse[BddFeatureResponse]):
    """Paginated list of BDD features for a story."""

    pass


class BddGenerateResponse(BaseSchema):
    """Result of an AI BDD generation run."""

    story_id: UUID
    feature: BddFeatureResponse
    summary: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    source_test_case_count: int = 0
    raw_response: Optional[Dict[str, Any]] = None
