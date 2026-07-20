"""
Map Jira Cloud payloads into platform domain field values.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.models.enums import Priority, StoryStatus, StoryType


def _adf_to_text(node: Any) -> str:
    """Flatten Atlassian Document Format (ADF) to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(_adf_to_text(item) for item in node if item)
    if isinstance(node, dict):
        if node.get("type") == "text":
            return str(node.get("text") or "")
        content = node.get("content") or []
        parts = [_adf_to_text(child) for child in content]
        text = "\n".join(p for p in parts if p)
        if node.get("type") in {"paragraph", "heading", "listItem"}:
            return text
        return text
    return str(node)


def jira_description_to_text(description: Any) -> Optional[str]:
    text = _adf_to_text(description).strip()
    return text or None


def parse_acceptance_criteria(
    description_text: Optional[str],
    custom_field_value: Any = None,
) -> List[str]:
    """
    Extract acceptance criteria lines from a custom field or description section.
    """
    if custom_field_value is not None:
        if isinstance(custom_field_value, str) and custom_field_value.strip():
            return [
                line.strip(" -*\t")
                for line in custom_field_value.splitlines()
                if line.strip()
            ]
        text = jira_description_to_text(custom_field_value)
        if text:
            return [
                line.strip(" -*\t")
                for line in text.splitlines()
                if line.strip()
            ]

    if not description_text:
        return []

    # Capture bullets under an "Acceptance Criteria" heading
    match = re.search(
        r"acceptance\s*criteria\s*:?\s*(.+?)(?:\n\s*\n|\Z)",
        description_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []
    block = match.group(1)
    return [
        line.strip(" -*\t")
        for line in block.splitlines()
        if line.strip() and not line.strip().lower().startswith("acceptance")
    ]


def map_priority(jira_priority: Optional[Dict[str, Any]]) -> Priority:
    name = (jira_priority or {}).get("name", "").lower()
    if name in {"highest", "blocker", "critical"}:
        return Priority.CRITICAL
    if name in {"high"}:
        return Priority.HIGH
    if name in {"low", "lowest"}:
        return Priority.LOW
    return Priority.MEDIUM


def map_status(jira_status: Optional[Dict[str, Any]]) -> StoryStatus:
    category = (
        ((jira_status or {}).get("statusCategory") or {}).get("key") or ""
    ).lower()
    name = ((jira_status or {}).get("name") or "").lower()

    if category == "done" or name in {"done", "closed", "resolved"}:
        return StoryStatus.DONE
    if name in {"blocked", "impediment"}:
        return StoryStatus.BLOCKED
    if category == "indeterminate" or "progress" in name or "review" in name:
        if "review" in name:
            return StoryStatus.IN_REVIEW
        return StoryStatus.IN_PROGRESS
    if name in {"ready", "selected for development", "to do", "open"}:
        return StoryStatus.READY if name == "ready" else StoryStatus.DRAFT
    if category == "new":
        return StoryStatus.DRAFT
    return StoryStatus.DRAFT


def map_story_type(jira_issuetype: Optional[Dict[str, Any]]) -> StoryType:
    name = ((jira_issuetype or {}).get("name") or "").lower()
    if "bug" in name or "defect" in name:
        return StoryType.BUG
    if "spike" in name:
        return StoryType.SPIKE
    if "task" in name or "sub-task" in name:
        return StoryType.TASK
    if "improvement" in name or "enhancement" in name:
        return StoryType.ENHANCEMENT
    return StoryType.FEATURE


def parse_jira_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    # Jira: 2024-01-15T10:30:00.000+0000
    normalized = value.replace("+0000", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def parse_jira_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def display_name(user: Optional[Dict[str, Any]]) -> Optional[str]:
    if not user:
        return None
    return user.get("displayName") or user.get("emailAddress") or user.get("accountId")


def extract_sprint_id_from_issue(fields: Dict[str, Any]) -> Optional[str]:
    """Best-effort sprint id from common custom fields / agile fields."""
    for key, value in fields.items():
        if not key.lower().startswith("customfield"):
            continue
        if isinstance(value, list) and value:
            last = value[-1]
            if isinstance(last, dict) and "id" in last:
                return str(last["id"])
            if isinstance(last, str) and "id=" in last:
                match = re.search(r"id=(\d+)", last)
                if match:
                    return match.group(1)
        if isinstance(value, dict) and "id" in value:
            return str(value["id"])
    return None


def map_issue(
    issue: Dict[str, Any],
    *,
    acceptance_criteria_field: Optional[str] = None,
) -> Dict[str, Any]:
    """Map a Jira issue JSON object to platform story field dict."""
    fields = issue.get("fields") or {}
    description = jira_description_to_text(fields.get("description"))
    ac_raw = (
        fields.get(acceptance_criteria_field)
        if acceptance_criteria_field
        else None
    )
    acceptance_criteria = parse_acceptance_criteria(description, ac_raw)

    return {
        "jira_issue_id": str(issue.get("id")),
        "external_id": issue.get("key"),
        "title": fields.get("summary") or issue.get("key") or "Untitled",
        "description": description,
        "status": map_status(fields.get("status")),
        "story_type": map_story_type(fields.get("issuetype")),
        "priority": map_priority(fields.get("priority")),
        "labels": list(fields.get("labels") or []),
        "assignee": display_name(fields.get("assignee")),
        "reporter": display_name(fields.get("reporter")),
        "external_updated_at": parse_jira_datetime(fields.get("updated")),
        "jira_created_at": parse_jira_datetime(fields.get("created")),
        "acceptance_criteria": acceptance_criteria,
        "jira_sprint_id": extract_sprint_id_from_issue(fields),
    }


def map_project(project: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "external_id": str(project.get("id")),
        "key": project.get("key") or "KEY",
        "name": project.get("name") or project.get("key") or "Jira Project",
        "description": project.get("description"),
    }


def map_sprint(sprint: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "external_id": str(sprint.get("id")),
        "name": sprint.get("name") or f"Sprint {sprint.get('id')}",
        "goal": sprint.get("goal"),
        "start_date": parse_jira_date(sprint.get("startDate")),
        "end_date": parse_jira_date(sprint.get("endDate")),
        "is_active": (sprint.get("state") or "").lower() == "active",
    }
