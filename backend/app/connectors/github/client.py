"""
Async GitHub REST client with pagination, rate-limit, and retry handling.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.connectors.exceptions import (
    ConnectorConnectionError,
    ConnectorCredentialError,
)
from app.connectors.github.constants import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT_SECONDS,
    GITHUB_API_BASE,
    MAX_RETRIES,
    RETRY_STATUSES,
)

logger = logging.getLogger(__name__)


class GitHubClient:
    """Thin async wrapper over the GitHub REST API."""

    def __init__(
        self,
        token: str,
        *,
        api_base_url: str = GITHUB_API_BASE,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.token = token
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def open(self) -> None:
        if self._client is not None:
            return
        if not self.token:
            raise ConnectorCredentialError("GitHub PAT (token) is required")
        self._client = httpx.AsyncClient(
            base_url=self.api_base_url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "AI-QA-Platform-GitHubConnector",
            },
            timeout=self.timeout,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        await self.open()
        assert self._client is not None

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method,
                    path,
                    params=params,
                    json=json,
                )
            except httpx.TransportError as exc:
                last_error = exc
                await asyncio.sleep(min(2**attempt, 8))
                continue

            if response.status_code in RETRY_STATUSES:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(2**attempt, 16)
                logger.warning(
                    "GitHub rate limit / transient error %s on %s %s — retry in %.1fs",
                    response.status_code,
                    method,
                    path,
                    delay,
                )
                await asyncio.sleep(delay)
                last_error = ConnectorConnectionError(
                    f"GitHub transient error {response.status_code}",
                    details={"path": path, "status": response.status_code},
                )
                continue

            if response.status_code == 401:
                raise ConnectorCredentialError(
                    "GitHub authentication failed — check Personal Access Token",
                    details={"status": 401},
                )

            if response.status_code == 403:
                remaining = response.headers.get("X-RateLimit-Remaining")
                if remaining == "0":
                    reset = response.headers.get("X-RateLimit-Reset")
                    delay = min(2**attempt, 16)
                    logger.warning(
                        "GitHub rate limit exhausted (reset=%s) — retry in %.1fs",
                        reset,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    last_error = ConnectorConnectionError(
                        "GitHub rate limit exceeded",
                        details={"path": path, "status": 403},
                    )
                    continue

            if response.status_code >= 400:
                raise ConnectorConnectionError(
                    f"GitHub API error {response.status_code}: {response.text[:300]}",
                    details={"status": response.status_code, "path": path},
                )

            if response.status_code == 204 or not response.content:
                return None
            return response.json()

        raise ConnectorConnectionError(
            f"GitHub request failed after {self.max_retries} retries: {path}",
            details={"error": str(last_error) if last_error else None},
        )

    async def paginate(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        item_key: Optional[str] = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> List[Dict[str, Any]]:
        """Collect all pages using Link-style page numbers."""
        items: List[Dict[str, Any]] = []
        page = 1
        query = dict(params or {})
        query.setdefault("per_page", page_size)

        while True:
            query["page"] = page
            data = await self.request("GET", path, params=query)
            if data is None:
                break
            if item_key:
                batch = data.get(item_key) or []
            elif isinstance(data, list):
                batch = data
            else:
                batch = []
            items.extend(batch)
            if len(batch) < page_size:
                break
            page += 1
        return items

    # ----- Auth / health -----

    async def get_authenticated_user(self) -> Dict[str, Any]:
        return await self.request("GET", "/user")

    async def timed_authenticated_user(self) -> Tuple[Dict[str, Any], float]:
        start = time.perf_counter()
        user = await self.get_authenticated_user()
        latency_ms = (time.perf_counter() - start) * 1000
        return user, latency_ms

    # ----- Refs / branches -----

    async def get_ref(self, owner: str, repo: str, ref: str) -> Dict[str, Any]:
        """Get a git ref. ``ref`` may be ``heads/main`` or ``main``."""
        normalized = ref if ref.startswith("heads/") or ref.startswith("tags/") else f"heads/{ref}"
        return await self.request(
            "GET",
            f"/repos/{owner}/{repo}/git/ref/{normalized}",
        )

    async def create_ref(
        self,
        owner: str,
        repo: str,
        *,
        ref: str,
        sha: str,
    ) -> Dict[str, Any]:
        full_ref = ref if ref.startswith("refs/") else f"refs/heads/{ref}"
        return await self.request(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            json={"ref": full_ref, "sha": sha},
        )

    async def update_ref(
        self,
        owner: str,
        repo: str,
        *,
        ref: str,
        sha: str,
        force: bool = False,
    ) -> Dict[str, Any]:
        normalized = ref if ref.startswith("heads/") or ref.startswith("tags/") else f"heads/{ref}"
        return await self.request(
            "PATCH",
            f"/repos/{owner}/{repo}/git/refs/{normalized}",
            json={"sha": sha, "force": force},
        )

    async def create_branch(
        self,
        owner: str,
        repo: str,
        *,
        branch_name: str,
        from_branch: str,
    ) -> Dict[str, Any]:
        base = await self.get_ref(owner, repo, from_branch)
        sha = base["object"]["sha"]
        return await self.create_ref(owner, repo, ref=branch_name, sha=sha)

    # ----- Commits (Git Data API) -----

    async def get_commit(self, owner: str, repo: str, sha: str) -> Dict[str, Any]:
        return await self.request("GET", f"/repos/{owner}/{repo}/git/commits/{sha}")

    async def create_blob(
        self,
        owner: str,
        repo: str,
        *,
        content: str,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        if encoding == "base64":
            payload = content
        else:
            payload = content
            encoding = "utf-8"
        return await self.request(
            "POST",
            f"/repos/{owner}/{repo}/git/blobs",
            json={"content": payload, "encoding": encoding},
        )

    async def create_tree(
        self,
        owner: str,
        repo: str,
        *,
        base_tree: str,
        tree: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return await self.request(
            "POST",
            f"/repos/{owner}/{repo}/git/trees",
            json={"base_tree": base_tree, "tree": tree},
        )

    async def create_commit(
        self,
        owner: str,
        repo: str,
        *,
        message: str,
        tree_sha: str,
        parents: List[str],
        author: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "message": message,
            "tree": tree_sha,
            "parents": parents,
        }
        if author:
            body["author"] = author
        return await self.request(
            "POST",
            f"/repos/{owner}/{repo}/git/commits",
            json=body,
        )

    async def commit_files(
        self,
        owner: str,
        repo: str,
        *,
        branch: str,
        message: str,
        files: List[Dict[str, str]],
        author: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a commit on ``branch`` with the given files and update the ref (push).

        Each file dict: ``{"path": "relative/path.ts", "content": "..."}``.
        """
        if not files:
            raise ConnectorConnectionError("At least one file is required to commit")

        ref = await self.get_ref(owner, repo, branch)
        parent_sha = ref["object"]["sha"]
        parent_commit = await self.get_commit(owner, repo, parent_sha)
        base_tree = parent_commit["tree"]["sha"]

        tree_entries: List[Dict[str, Any]] = []
        for file_entry in files:
            path = file_entry.get("path") or ""
            content = file_entry.get("content")
            if not path or content is None:
                raise ConnectorConnectionError(
                    "Each file requires path and content",
                    details={"file": file_entry},
                )
            # Prefer utf-8 text; fall back to base64 for binary-looking content
            try:
                content.encode("utf-8")
                blob = await self.create_blob(
                    owner, repo, content=content, encoding="utf-8"
                )
            except UnicodeEncodeError:
                encoded = base64.b64encode(content.encode("utf-8", errors="replace")).decode(
                    "ascii"
                )
                blob = await self.create_blob(
                    owner, repo, content=encoded, encoding="base64"
                )
            tree_entries.append(
                {
                    "path": path.lstrip("/"),
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob["sha"],
                }
            )

        new_tree = await self.create_tree(
            owner, repo, base_tree=base_tree, tree=tree_entries
        )
        commit = await self.create_commit(
            owner,
            repo,
            message=message,
            tree_sha=new_tree["sha"],
            parents=[parent_sha],
            author=author,
        )
        updated_ref = await self.update_ref(
            owner, repo, ref=branch, sha=commit["sha"]
        )
        return {
            "commit": commit,
            "ref": updated_ref,
            "sha": commit["sha"],
            "tree_sha": new_tree["sha"],
            "files_committed": len(files),
            "branch": branch,
        }

    # ----- Pull requests -----

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        *,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
        draft: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "title": title,
            "head": head,
            "base": base,
            "draft": draft,
        }
        if body is not None:
            payload["body"] = body
        return await self.request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            json=payload,
        )

    # ----- Status checks -----

    async def get_combined_status(
        self,
        owner: str,
        repo: str,
        ref: str,
    ) -> Dict[str, Any]:
        """Combined commit status for a SHA or branch name."""
        return await self.request(
            "GET",
            f"/repos/{owner}/{repo}/commits/{ref}/status",
        )

    async def list_check_runs(
        self,
        owner: str,
        repo: str,
        ref: str,
    ) -> Dict[str, Any]:
        """Check runs for a commit SHA or branch (best-effort; may be empty)."""
        return await self.request(
            "GET",
            f"/repos/{owner}/{repo}/commits/{ref}/check-runs",
            params={"per_page": DEFAULT_PAGE_SIZE},
        )
