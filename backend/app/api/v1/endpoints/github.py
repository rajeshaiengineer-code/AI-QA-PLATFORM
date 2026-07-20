"""
GitHub Connector API endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import ErrorResponse
from app.schemas.github import (
    GitHubCommitRequest,
    GitHubCommitResponse,
    GitHubConnectRequest,
    GitHubConnectResponse,
    GitHubCreateBranchRequest,
    GitHubCreateBranchResponse,
    GitHubHealthResponse,
    GitHubMessageResponse,
    GitHubPullRequestRequest,
    GitHubPullRequestResponse,
    GitHubPushRequest,
    GitHubStatusChecksResponse,
)
from app.services.github_connector import GitHubConnectorService

router = APIRouter()


def get_github_service(
    db: AsyncSession = Depends(get_db),
) -> GitHubConnectorService:
    return GitHubConnectorService(session=db)


@router.post(
    "/connect",
    response_model=GitHubConnectResponse,
    status_code=status.HTTP_200_OK,
    summary="Connect to GitHub",
    description=(
        "Validate and store a GitHub Personal Access Token via the "
        "Connector Framework Credential Manager, then open a session."
    ),
    responses={400: {"model": ErrorResponse}},
)
async def connect_github(
    payload: GitHubConnectRequest,
    service: GitHubConnectorService = Depends(get_github_service),
) -> GitHubConnectResponse:
    return await service.connect(payload)


@router.post(
    "/disconnect",
    response_model=GitHubMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Disconnect from GitHub",
    description="Close the GitHub session and remove stored credentials/config.",
)
async def disconnect_github(
    service: GitHubConnectorService = Depends(get_github_service),
) -> GitHubMessageResponse:
    return await service.disconnect()


@router.get(
    "/health",
    response_model=GitHubHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="GitHub connector health check",
    description="Returns status, version, latency_ms, and last_checked.",
    responses={400: {"model": ErrorResponse}},
)
async def github_health(
    service: GitHubConnectorService = Depends(get_github_service),
) -> GitHubHealthResponse:
    return await service.health()


@router.post(
    "/create-branch",
    response_model=GitHubCreateBranchResponse,
    status_code=status.HTTP_200_OK,
    summary="Create a Git branch",
    description="Create a branch from an existing base branch (default: main).",
    responses={400: {"model": ErrorResponse}},
)
async def create_branch(
    payload: GitHubCreateBranchRequest,
    service: GitHubConnectorService = Depends(get_github_service),
) -> GitHubCreateBranchResponse:
    return await service.create_branch(payload)


@router.post(
    "/commit",
    response_model=GitHubCommitResponse,
    status_code=status.HTTP_200_OK,
    summary="Commit and push files",
    description=(
        "Create a commit on a branch with explicit files or contents from an "
        "AutomationArtifact, then update the branch ref (push)."
    ),
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def commit_files(
    payload: GitHubCommitRequest,
    service: GitHubConnectorService = Depends(get_github_service),
) -> GitHubCommitResponse:
    return await service.commit(payload)


@router.post(
    "/push",
    response_model=GitHubCommitResponse,
    status_code=status.HTTP_200_OK,
    summary="Push (commit + update ref)",
    description=(
        "Same as POST /commit — GitHub has no separate push over REST; "
        "updating the branch ref publishes the commit."
    ),
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def push_files(
    payload: GitHubPushRequest,
    service: GitHubConnectorService = Depends(get_github_service),
) -> GitHubCommitResponse:
    return await service.push(payload)


@router.post(
    "/pull-request",
    response_model=GitHubPullRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Create a pull request",
    description="Open a pull request from head → base.",
    responses={400: {"model": ErrorResponse}},
)
async def create_pull_request(
    payload: GitHubPullRequestRequest,
    service: GitHubConnectorService = Depends(get_github_service),
) -> GitHubPullRequestResponse:
    return await service.create_pull_request(payload)


@router.get(
    "/status-checks",
    response_model=GitHubStatusChecksResponse,
    status_code=status.HTTP_200_OK,
    summary="Get commit status checks",
    description=(
        "Return combined commit statuses and check runs for a branch or SHA."
    ),
    responses={400: {"model": ErrorResponse}},
)
async def status_checks(
    ref: str = Query(..., description="Branch name or commit SHA"),
    owner: Optional[str] = Query(None, description="Override default owner"),
    repo: Optional[str] = Query(None, description="Override default repo"),
    service: GitHubConnectorService = Depends(get_github_service),
) -> GitHubStatusChecksResponse:
    return await service.status_checks(ref=ref, owner=owner, repo=repo)
