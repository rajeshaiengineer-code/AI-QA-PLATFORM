"""
Playwright Automation Artifact API Endpoints

Retrieve generated Playwright TypeScript artifacts by id.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import ErrorResponse
from app.schemas.automation_artifact import AutomationArtifactResponse
from app.services.playwright_generator import PlaywrightGeneratorService

router = APIRouter()


def get_playwright_generator_service(
    db: AsyncSession = Depends(get_db),
) -> PlaywrightGeneratorService:
    """Dependency that builds a PlaywrightGeneratorService for the request session."""
    return PlaywrightGeneratorService(db)


@router.get(
    "/{artifact_id}",
    response_model=AutomationArtifactResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Playwright artifact by ID",
    description=(
        "Retrieve a single generated Playwright TypeScript automation artifact "
        "(page objects, locators, fixtures, utilities, assertions, hooks, specs)."
    ),
    tags=["Playwright", "AI"],
    responses={
        404: {"model": ErrorResponse, "description": "Automation artifact not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_playwright_artifact(
    artifact_id: UUID,
    service: PlaywrightGeneratorService = Depends(get_playwright_generator_service),
) -> AutomationArtifactResponse:
    """Get a Playwright automation artifact by id."""
    return await service.get_artifact(artifact_id)
