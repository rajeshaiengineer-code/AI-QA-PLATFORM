"""
BDD Feature API Endpoints

Retrieve generated Gherkin features by id.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import ErrorResponse
from app.schemas.bdd_feature import BddFeatureResponse
from app.services.bdd_generator import BddGeneratorService

router = APIRouter()


def get_bdd_generator_service(
    db: AsyncSession = Depends(get_db),
) -> BddGeneratorService:
    """Dependency that builds a BddGeneratorService for the request session."""
    return BddGeneratorService(db)


@router.get(
    "/{feature_id}",
    response_model=BddFeatureResponse,
    status_code=status.HTTP_200_OK,
    summary="Get BDD feature by ID",
    description="Retrieve a single generated Gherkin feature artifact by UUID.",
    tags=["BDD", "AI"],
    responses={
        404: {"model": ErrorResponse, "description": "BDD feature not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_bdd_feature(
    feature_id: UUID,
    service: BddGeneratorService = Depends(get_bdd_generator_service),
) -> BddFeatureResponse:
    """Get a BDD feature by id."""
    return await service.get_bdd_feature(feature_id)
