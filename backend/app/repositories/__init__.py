"""
Repositories Module

Contains data access layer classes.
"""

from app.repositories.base import BaseRepository
from app.repositories.automation_artifact import AutomationArtifactRepository
from app.repositories.automation_job import AutomationJobRepository
from app.repositories.bdd_feature import BddFeatureRepository
from app.repositories.bug import BugRepository
from app.repositories.execution import ExecutionRepository
from app.repositories.failure_analysis import FailureAnalysisRepository
from app.repositories.notification import NotificationLogRepository
from app.repositories.story import StoryRepository
from app.repositories.story_analysis import StoryAnalysisRepository
from app.repositories.test_case import TestCaseRepository
from app.repositories.test_case_version import TestCaseVersionRepository
from app.repositories.user import OrganizationMembershipRepository, UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "OrganizationMembershipRepository",
    "StoryRepository",
    "StoryAnalysisRepository",
    "TestCaseRepository",
    "TestCaseVersionRepository",
    "BddFeatureRepository",
    "AutomationArtifactRepository",
    "AutomationJobRepository",
    "ExecutionRepository",
    "FailureAnalysisRepository",
    "BugRepository",
    "NotificationLogRepository",
]
