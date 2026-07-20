"""
Automation Artifact Pydantic Schemas

Request/response models for AI Playwright Generator APIs.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.base import BaseSchema, PaginatedResponse


ArtifactKind = Literal[
    "page_object",
    "locator",
    "fixture",
    "utility",
    "assertion",
    "hook",
    "spec",
]


class AutomationFileDraft(BaseSchema):
    """Single generated file with relative path and TypeScript content."""

    path: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    description: Optional[str] = None
    kind: Optional[ArtifactKind] = Field(
        None,
        description="Optional kind hint; used when files are provided in a flat list.",
    )

    @field_validator("path")
    @classmethod
    def normalize_path(cls, value: str) -> str:
        cleaned = value.strip().lstrip("/")
        if not cleaned:
            raise ValueError("path must not be blank")
        return cleaned


class PlaywrightSuiteDraft(BaseSchema):
    """Structured Playwright suite envelope returned by the LLM."""

    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    language: str = "typescript"
    framework: str = "playwright"
    page_objects: List[AutomationFileDraft] = Field(default_factory=list)
    locators: List[AutomationFileDraft] = Field(default_factory=list)
    fixtures: List[AutomationFileDraft] = Field(default_factory=list)
    utilities: List[AutomationFileDraft] = Field(default_factory=list)
    assertions: List[AutomationFileDraft] = Field(default_factory=list)
    hooks: List[AutomationFileDraft] = Field(default_factory=list)
    specs: List[AutomationFileDraft] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_some_files(self) -> "PlaywrightSuiteDraft":
        total = (
            len(self.page_objects)
            + len(self.locators)
            + len(self.fixtures)
            + len(self.utilities)
            + len(self.assertions)
            + len(self.hooks)
            + len(self.specs)
        )
        if total == 0:
            raise ValueError("suite must include at least one generated file")
        return self


class PlaywrightGenerateResult(BaseSchema):
    """Top-level LLM JSON envelope for Playwright generation."""

    suite: PlaywrightSuiteDraft
    summary: Optional[str] = None


class PlaywrightGenerateRequest(BaseSchema):
    """Optional overrides when triggering Playwright generation."""

    logical_model: Optional[str] = Field(
        None,
        description="Logical model alias from ModelRegistry (default: 'default').",
        examples=["default", "fast", "balanced"],
    )
    use_bdd: bool = Field(
        True,
        description="Include latest BDD / Gherkin features for the story as input.",
    )
    use_test_cases: bool = Field(
        True,
        description="Include eligible test cases as input.",
    )
    include_drafts: bool = Field(
        False,
        description=(
            "When false (default), only approved test cases are used. "
            "When true, also include draft and pending_review cases "
            "(rejected cases are never included)."
        ),
    )

    @model_validator(mode="after")
    def require_source(self) -> "PlaywrightGenerateRequest":
        if not self.use_bdd and not self.use_test_cases:
            raise ValueError("at least one of use_bdd or use_test_cases must be true")
        return self


class AutomationArtifactResponse(BaseSchema):
    """Persisted Playwright automation artifact returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440040",
                "story_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "password-reset",
                "description": "Playwright suite for password reset",
                "language": "typescript",
                "framework": "playwright",
                "page_objects": [
                    {
                        "path": "pages/PasswordResetPage.ts",
                        "content": "export class PasswordResetPage { ... }",
                    }
                ],
                "locators": [
                    {
                        "path": "locators/passwordReset.ts",
                        "content": "export const passwordReset = { ... };",
                    }
                ],
                "fixtures": [],
                "utilities": [],
                "assertions": [],
                "hooks": [],
                "specs": [
                    {
                        "path": "tests/password-reset.spec.ts",
                        "content": "import { test, expect } from '@playwright/test';",
                    }
                ],
                "source_bdd_feature_ids": ["550e8400-e29b-41d4-a716-446655440030"],
                "source_test_case_ids": ["550e8400-e29b-41d4-a716-446655440020"],
                "use_bdd": True,
                "use_test_cases": True,
                "include_drafts": False,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "summary": "Generated page object + spec for password reset.",
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
    language: str = "typescript"
    framework: str = "playwright"
    page_objects: Optional[List[Any]] = None
    locators: Optional[List[Any]] = None
    fixtures: Optional[List[Any]] = None
    utilities: Optional[List[Any]] = None
    assertions: Optional[List[Any]] = None
    hooks: Optional[List[Any]] = None
    specs: Optional[List[Any]] = None
    source_bdd_feature_ids: Optional[List[Any]] = None
    source_test_case_ids: Optional[List[Any]] = None
    use_bdd: bool = True
    use_test_cases: bool = True
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


class AutomationArtifactListResponse(PaginatedResponse[AutomationArtifactResponse]):
    """Paginated list of automation artifacts for a story."""

    pass


class PlaywrightGenerateResponse(BaseSchema):
    """Result of an AI Playwright generation run."""

    story_id: UUID
    artifact: AutomationArtifactResponse
    summary: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    source_bdd_feature_count: int = 0
    source_test_case_count: int = 0
    file_count: int = 0
    raw_response: Optional[Dict[str, Any]] = None
