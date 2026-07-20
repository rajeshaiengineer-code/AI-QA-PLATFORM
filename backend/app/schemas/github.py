"""
Pydantic schemas for GitHub connector APIs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class GitHubConnectRequest(BaseSchema):
    """Connect / save GitHub PAT + optional default repo settings."""

    personal_access_token: str = Field(
        ...,
        min_length=8,
        description="GitHub Personal Access Token (classic or fine-grained)",
    )
    api_base_url: Optional[str] = Field(
        None,
        description="Override API base (GitHub Enterprise). Default: https://api.github.com",
        examples=["https://api.github.com"],
    )
    owner: Optional[str] = Field(
        None,
        description="Default repository owner (org or user)",
        examples=["acme-org"],
    )
    repo: Optional[str] = Field(
        None,
        description="Default repository name",
        examples=["qa-automation"],
    )
    default_base_branch: Optional[str] = Field(
        None,
        description="Default base branch for create-branch / PRs",
        examples=["main"],
    )


class GitHubConnectResponse(BaseSchema):
    connected: bool
    message: str
    login: Optional[str] = None
    owner: Optional[str] = None
    repo: Optional[str] = None


class GitHubHealthResponse(BaseSchema):
    status: str
    version: Optional[str] = None
    latency_ms: Optional[float] = None
    last_checked: datetime
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class GitHubMessageResponse(BaseSchema):
    success: bool = True
    message: str


class GitHubFileContent(BaseSchema):
    path: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)


class GitHubCreateBranchRequest(BaseSchema):
    branch_name: str = Field(..., min_length=1, max_length=255)
    from_branch: Optional[str] = Field(
        None,
        description="Source branch (default: connector default_base_branch or main)",
    )
    owner: Optional[str] = None
    repo: Optional[str] = None


class GitHubCreateBranchResponse(BaseSchema):
    owner: str
    repo: str
    branch: str
    from_branch: str
    ref: Optional[str] = None
    sha: Optional[str] = None


class GitHubCommitRequest(BaseSchema):
    """Commit files to a branch (also updates the ref — push)."""

    branch: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    files: Optional[List[GitHubFileContent]] = Field(
        None,
        description="Explicit file list. Ignored when automation_artifact_id is set.",
    )
    automation_artifact_id: Optional[UUID] = Field(
        None,
        description=(
            "Load file contents from a persisted AutomationArtifact "
            "(page_objects, specs, …)."
        ),
    )
    owner: Optional[str] = None
    repo: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None


class GitHubCommitResponse(BaseSchema):
    owner: str
    repo: str
    branch: str
    sha: str
    tree_sha: Optional[str] = None
    files_committed: int
    html_url: Optional[str] = None
    message: str = "Commit created and ref updated (pushed)"


class GitHubPushRequest(BaseSchema):
    """
    Alias for commit+push. Prefer POST /commit; this endpoint exists for
    explicit push semantics and accepts the same payload.
    """

    branch: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    files: Optional[List[GitHubFileContent]] = None
    automation_artifact_id: Optional[UUID] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None


class GitHubPullRequestRequest(BaseSchema):
    title: str = Field(..., min_length=1, max_length=500)
    head: str = Field(..., description="Head branch name (or owner:branch for forks)")
    base: Optional[str] = Field(None, description="Base branch (default: main)")
    body: Optional[str] = None
    draft: bool = False
    owner: Optional[str] = None
    repo: Optional[str] = None


class GitHubPullRequestResponse(BaseSchema):
    owner: str
    repo: str
    number: Optional[int] = None
    html_url: Optional[str] = None
    title: Optional[str] = None
    state: Optional[str] = None
    head: str
    base: str
    draft: Optional[bool] = None


class GitHubStatusCheckItem(BaseSchema):
    context: Optional[str] = None
    state: Optional[str] = None
    description: Optional[str] = None
    target_url: Optional[str] = None


class GitHubCheckRunItem(BaseSchema):
    id: Optional[int] = None
    name: Optional[str] = None
    status: Optional[str] = None
    conclusion: Optional[str] = None
    html_url: Optional[str] = None


class GitHubStatusChecksResponse(BaseSchema):
    owner: str
    repo: str
    ref: str
    state: Optional[str] = None
    total_count: Optional[int] = None
    statuses: List[GitHubStatusCheckItem] = Field(default_factory=list)
    check_runs: List[GitHubCheckRunItem] = Field(default_factory=list)
    check_runs_total: int = 0
