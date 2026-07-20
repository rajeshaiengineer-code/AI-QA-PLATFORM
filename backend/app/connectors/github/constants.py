"""GitHub connector constants."""

GITHUB_CONNECTOR_NAME = "github"

# REST API root (relative to api.github.com by default)
GITHUB_API_BASE = "https://api.github.com"

DEFAULT_PAGE_SIZE = 100
MAX_RETRIES = 5
RETRY_STATUSES = {429, 502, 503, 504}
DEFAULT_TIMEOUT_SECONDS = 30.0

# Common default branch names used when resolving base refs
DEFAULT_BASE_BRANCH = "main"
