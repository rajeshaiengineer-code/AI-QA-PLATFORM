"""WorkflowState — single source of progress for a story run."""

from enum import Enum


class WorkflowState(str, Enum):
    NEW = "new"
    SYNCED = "synced"
    ANALYZED = "analyzed"
    TEST_CASES_GENERATED = "test_cases_generated"
    QA_APPROVED = "qa_approved"
    BDD_GENERATED = "bdd_generated"
    AUTOMATION_GENERATED = "automation_generated"
    PR_CREATED = "pr_created"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    FAILURE_ANALYZED = "failure_analyzed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
