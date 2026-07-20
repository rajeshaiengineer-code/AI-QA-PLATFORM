"""Jira Cloud connector constants."""

JIRA_CONNECTOR_NAME = "jira"

# REST API roots (relative to site base URL, e.g. https://acme.atlassian.net)
JIRA_API_V3 = "/rest/api/3"
JIRA_AGILE_V1 = "/rest/agile/1.0"

DEFAULT_PAGE_SIZE = 50
MAX_RETRIES = 5
RETRY_STATUSES = {429, 502, 503, 504}
DEFAULT_TIMEOUT_SECONDS = 30.0

ISSUE_FIELDS = [
    "summary",
    "description",
    "status",
    "issuetype",
    "priority",
    "labels",
    "assignee",
    "reporter",
    "created",
    "updated",
    "parent",
    "customfield_10020",  # common Sprint field (team-managed varies)
]
