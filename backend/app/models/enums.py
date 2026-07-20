"""
Domain Enumerations

PostgreSQL-backed string enums for constrained domain values.
"""

from enum import Enum


class StoryStatus(str, Enum):
    """Lifecycle status of a user story."""

    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"


class StoryType(str, Enum):
    """Classification of a work item / story."""

    FEATURE = "feature"
    BUG = "bug"
    TASK = "task"
    SPIKE = "spike"
    ENHANCEMENT = "enhancement"


class Priority(str, Enum):
    """Shared priority scale for stories, test cases, and bugs."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AutomationStatus(str, Enum):
    """Lifecycle status of an automation job."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStatus(str, Enum):
    """Outcome status of a single test execution."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    BLOCKED = "blocked"


class BugStatus(str, Enum):
    """Lifecycle status of a defect."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    VERIFIED = "verified"
    CLOSED = "closed"
    REOPENED = "reopened"


class FailureCategory(str, Enum):
    """AI classification of a failed test execution."""

    PRODUCT_BUG = "product_bug"
    TEST_BUG = "test_bug"
    FLAKY = "flaky"
    ENVIRONMENT = "environment"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class ComplexityLevel(str, Enum):
    """Estimated implementation / test complexity of a story."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(str, Enum):
    """Estimated delivery / quality risk of a story."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TestCaseCategory(str, Enum):
    """QA category for a generated or authored test case."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"
    API = "api"
    SECURITY = "security"
    DATABASE = "database"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"


class TestCaseSource(str, Enum):
    """Origin of a test case definition."""

    __test__ = False  # not a pytest test class

    AI = "ai"
    MANUAL = "manual"
    IMPORTED = "imported"


class TestCaseStatus(str, Enum):
    """QA review lifecycle status of a test case."""

    __test__ = False  # not a pytest test class

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class OrganizationRole(str, Enum):
    """Role of a user within an organization (RBAC)."""

    ADMIN = "admin"
    QA = "qa"
    ENGINEER = "engineer"
    VIEWER = "viewer"


class NotificationChannel(str, Enum):
    """Delivery channel for outbound notifications."""

    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"


class NotificationStatus(str, Enum):
    """Outcome of a notification send attempt."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"
