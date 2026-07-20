"""
Schemas Module

Contains Pydantic schemas for request/response validation.
"""

from app.schemas.base import (
    BaseSchema,
    TimestampSchema,
    PaginatedResponse,
    SuccessResponse,
    MessageResponse,
)
from app.schemas.story import (
    StoryCreate,
    StoryUpdate,
    StoryResponse,
    StoryListResponse,
    StoryFilterParams,
)
from app.schemas.story_analysis import (
    StoryAnalysisResponse,
    StoryAnalyzeRequest,
    StoryAnalysisResult,
)
from app.schemas.test_case import (
    TestCaseApproveAllResponse,
    TestCaseApproveRequest,
    TestCaseDecisionResponse,
    TestCaseGenerateRequest,
    TestCaseGenerateResponse,
    TestCaseListResponse,
    TestCaseRejectRequest,
    TestCaseResponse,
    TestCaseUpdate,
    TestCaseVersionListResponse,
    TestCaseVersionResponse,
)
from app.schemas.bdd_feature import (
    BddFeatureListResponse,
    BddFeatureResponse,
    BddGenerateRequest,
    BddGenerateResponse,
)
from app.schemas.automation_artifact import (
    AutomationArtifactListResponse,
    AutomationArtifactResponse,
    PlaywrightGenerateRequest,
    PlaywrightGenerateResponse,
)
from app.schemas.execution import (
    AutomationJobResponse,
    ExecutionDetailResponse,
    ExecutionListResponse,
    ExecutionResponse,
    ExecutionRunRequest,
    ExecutionRunResponse,
)
from app.schemas.failure_analysis import (
    FailureAnalysisResponse,
    FailureAnalyzeRequest,
    FailureAnalysisResult,
)
from app.schemas.bug import (
    BugResponse,
    CreateJiraBugRequest,
    CreateJiraBugResponse,
)
from app.schemas.auth import (
    LoginRequest,
    MembershipResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.notification import (
    NotificationListResponse,
    NotificationLogResponse,
    NotificationSendRequest,
    NotificationSendResponse,
)

__all__ = [
    "BaseSchema",
    "TimestampSchema",
    "PaginatedResponse",
    "SuccessResponse",
    "MessageResponse",
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "TokenResponse",
    "UserResponse",
    "MembershipResponse",
    "StoryCreate",
    "StoryUpdate",
    "StoryResponse",
    "StoryListResponse",
    "StoryFilterParams",
    "StoryAnalysisResponse",
    "StoryAnalyzeRequest",
    "StoryAnalysisResult",
    "TestCaseResponse",
    "TestCaseListResponse",
    "TestCaseGenerateRequest",
    "TestCaseGenerateResponse",
    "TestCaseUpdate",
    "TestCaseApproveRequest",
    "TestCaseRejectRequest",
    "TestCaseApproveAllResponse",
    "TestCaseDecisionResponse",
    "TestCaseVersionResponse",
    "TestCaseVersionListResponse",
    "BddFeatureResponse",
    "BddFeatureListResponse",
    "BddGenerateRequest",
    "BddGenerateResponse",
    "AutomationArtifactResponse",
    "AutomationArtifactListResponse",
    "PlaywrightGenerateRequest",
    "PlaywrightGenerateResponse",
    "ExecutionRunRequest",
    "ExecutionRunResponse",
    "ExecutionResponse",
    "ExecutionDetailResponse",
    "ExecutionListResponse",
    "AutomationJobResponse",
    "FailureAnalysisResponse",
    "FailureAnalyzeRequest",
    "FailureAnalysisResult",
    "BugResponse",
    "CreateJiraBugRequest",
    "CreateJiraBugResponse",
    "NotificationSendRequest",
    "NotificationSendResponse",
    "NotificationLogResponse",
    "NotificationListResponse",
]
