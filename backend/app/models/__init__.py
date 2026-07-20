"""
Models Module

SQLAlchemy ORM domain models.
Import all models here so Alembic can detect metadata.
"""

from app.core.database import Base
from app.models.acceptance_criteria import AcceptanceCriteria
from app.models.automation_artifact import AutomationArtifact
from app.models.automation_job import AutomationJob
from app.models.base import BaseEntity
from app.models.bdd_feature import BddFeature
from app.models.bug import Bug
from app.models.enums import (
    AutomationStatus,
    BugStatus,
    ComplexityLevel,
    ExecutionStatus,
    FailureCategory,
    NotificationChannel,
    NotificationStatus,
    OrganizationRole,
    Priority,
    RiskLevel,
    StoryStatus,
    StoryType,
    TestCaseCategory,
    TestCaseSource,
    TestCaseStatus,
)
from app.models.execution import Execution
from app.models.failure_analysis import FailureAnalysis
from app.models.notification_log import NotificationLog
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.story import Story
from app.models.story_analysis import StoryAnalysis
from app.models.sync_history import SyncHistory
from app.models.test_case import TestCase
from app.models.test_case_version import TestCaseVersion
from app.models.user import User
from app.models.workflow_log import WorkflowLog
from app.models.workflow_run import WorkflowRun

__all__ = [
    "Base",
    "BaseEntity",
    "Organization",
    "OrganizationMembership",
    "User",
    "Project",
    "Sprint",
    "Story",
    "StoryAnalysis",
    "AcceptanceCriteria",
    "TestCase",
    "TestCaseVersion",
    "BddFeature",
    "AutomationArtifact",
    "AutomationJob",
    "Execution",
    "FailureAnalysis",
    "Bug",
    "NotificationLog",
    "SyncHistory",
    "WorkflowRun",
    "WorkflowLog",
    "StoryStatus",
    "StoryType",
    "Priority",
    "AutomationStatus",
    "ExecutionStatus",
    "BugStatus",
    "FailureCategory",
    "ComplexityLevel",
    "RiskLevel",
    "TestCaseCategory",
    "TestCaseSource",
    "TestCaseStatus",
    "OrganizationRole",
    "NotificationChannel",
    "NotificationStatus",
]
