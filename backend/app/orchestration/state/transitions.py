"""Allowed WorkflowState transitions driven by WorkflowEvent."""

from typing import Dict, Optional, Set, Tuple

from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.state.enums import WorkflowState

# (from_state, event) -> to_state
_TRANSITIONS: Dict[Tuple[WorkflowState, WorkflowEvent], WorkflowState] = {
    (WorkflowState.NEW, WorkflowEvent.STORY_IMPORTED): WorkflowState.SYNCED,
    (WorkflowState.NEW, WorkflowEvent.STORY_SYNCED): WorkflowState.SYNCED,
    (WorkflowState.NEW, WorkflowEvent.IMPORT_FAILED): WorkflowState.FAILED,
    (WorkflowState.SYNCED, WorkflowEvent.STORY_ANALYZED): WorkflowState.ANALYZED,
    (WorkflowState.SYNCED, WorkflowEvent.ANALYSIS_FAILED): WorkflowState.FAILED,
    (
        WorkflowState.ANALYZED,
        WorkflowEvent.TEST_CASES_GENERATED,
    ): WorkflowState.TEST_CASES_GENERATED,
    (WorkflowState.ANALYZED, WorkflowEvent.TEST_GEN_FAILED): WorkflowState.FAILED,
    (
        WorkflowState.TEST_CASES_GENERATED,
        WorkflowEvent.STORY_APPROVED,
    ): WorkflowState.QA_APPROVED,
    (
        WorkflowState.TEST_CASES_GENERATED,
        WorkflowEvent.QA_REJECTED_TERMINAL,
    ): WorkflowState.FAILED,
    (
        WorkflowState.TEST_CASES_GENERATED,
        WorkflowEvent.STORY_REJECTED,
    ): WorkflowState.FAILED,
    (
        WorkflowState.QA_APPROVED,
        WorkflowEvent.BDD_GENERATED,
    ): WorkflowState.BDD_GENERATED,
    (WorkflowState.QA_APPROVED, WorkflowEvent.BDD_FAILED): WorkflowState.FAILED,
    (
        WorkflowState.BDD_GENERATED,
        WorkflowEvent.AUTOMATION_GENERATED,
    ): WorkflowState.AUTOMATION_GENERATED,
    (
        WorkflowState.BDD_GENERATED,
        WorkflowEvent.AUTOMATION_FAILED,
    ): WorkflowState.FAILED,
    (
        WorkflowState.AUTOMATION_GENERATED,
        WorkflowEvent.PULL_REQUEST_CREATED,
    ): WorkflowState.PR_CREATED,
    (
        WorkflowState.AUTOMATION_GENERATED,
        WorkflowEvent.PR_FAILED,
    ): WorkflowState.FAILED,
    (
        WorkflowState.PR_CREATED,
        WorkflowEvent.EXECUTION_STARTED,
    ): WorkflowState.EXECUTION_STARTED,
    (
        WorkflowState.PR_CREATED,
        WorkflowEvent.EXECUTION_FAILED_TO_START,
    ): WorkflowState.FAILED,
    (
        WorkflowState.EXECUTION_STARTED,
        WorkflowEvent.EXECUTION_COMPLETED,
    ): WorkflowState.EXECUTION_COMPLETED,
    (
        WorkflowState.EXECUTION_STARTED,
        WorkflowEvent.EXECUTION_ABORTED,
    ): WorkflowState.FAILED,
    (
        WorkflowState.EXECUTION_STARTED,
        WorkflowEvent.EXECUTION_FAILED,
    ): WorkflowState.FAILED,
    (
        WorkflowState.EXECUTION_COMPLETED,
        WorkflowEvent.REPORT_PUBLISHED,
    ): WorkflowState.COMPLETED,
    (
        WorkflowState.EXECUTION_COMPLETED,
        WorkflowEvent.BUGS_FILED_AND_REPORT_PUBLISHED,
    ): WorkflowState.COMPLETED,
    (
        WorkflowState.EXECUTION_COMPLETED,
        WorkflowEvent.CRITICAL_POLICY_BREACH,
    ): WorkflowState.FAILED,
    (
        WorkflowState.EXECUTION_COMPLETED,
        WorkflowEvent.FAILURE_ANALYZED,
    ): WorkflowState.FAILURE_ANALYZED,
    (
        WorkflowState.FAILURE_ANALYZED,
        WorkflowEvent.BUG_CREATED,
    ): WorkflowState.COMPLETED,
    (
        WorkflowState.FAILURE_ANALYZED,
        WorkflowEvent.BUGS_FILED_AND_REPORT_PUBLISHED,
    ): WorkflowState.COMPLETED,
    (
        WorkflowState.FAILURE_ANALYZED,
        WorkflowEvent.REPORT_PUBLISHED,
    ): WorkflowState.COMPLETED,
    (
        WorkflowState.FAILURE_ANALYZED,
        WorkflowEvent.CRITICAL_POLICY_BREACH,
    ): WorkflowState.FAILED,
}

# Events that may cancel a non-terminal run from any state
_CANCEL_EVENTS: Set[WorkflowEvent] = {WorkflowEvent.WORKFLOW_CANCELLED}


class TransitionError(Exception):
    """Raised when an event is not valid for the current state."""

    def __init__(
        self,
        current: WorkflowState,
        event: WorkflowEvent,
        message: Optional[str] = None,
    ) -> None:
        self.current = current
        self.event = event
        super().__init__(
            message
            or f"Invalid transition: state={current.value} event={event.value}"
        )


def transition_for(
    current: WorkflowState,
    event: WorkflowEvent,
) -> WorkflowState:
    """Return next state or raise TransitionError."""
    if current.is_terminal and event not in _CANCEL_EVENTS:
        raise TransitionError(
            current,
            event,
            f"Terminal state '{current.value}' cannot accept '{event.value}'",
        )

    if event in _CANCEL_EVENTS:
        if current.is_terminal:
            raise TransitionError(current, event, "Already terminal")
        return WorkflowState.CANCELLED

    key = (current, event)
    if key not in _TRANSITIONS:
        raise TransitionError(current, event)
    return _TRANSITIONS[key]


def next_auto_event(state: WorkflowState) -> Optional[WorkflowEvent]:
    """
    Suggest the primary happy-path event that advances from `state`.

    Used by advance() when an agent is not available (manual/test drives).
    """
    mapping = {
        WorkflowState.NEW: WorkflowEvent.STORY_IMPORTED,
        WorkflowState.SYNCED: WorkflowEvent.STORY_ANALYZED,
        WorkflowState.ANALYZED: WorkflowEvent.TEST_CASES_GENERATED,
        WorkflowState.TEST_CASES_GENERATED: None,  # waits for QA approve
        WorkflowState.QA_APPROVED: WorkflowEvent.BDD_GENERATED,
        WorkflowState.BDD_GENERATED: WorkflowEvent.AUTOMATION_GENERATED,
        WorkflowState.AUTOMATION_GENERATED: WorkflowEvent.PULL_REQUEST_CREATED,
        WorkflowState.PR_CREATED: WorkflowEvent.EXECUTION_STARTED,
        WorkflowState.EXECUTION_STARTED: WorkflowEvent.EXECUTION_COMPLETED,
        WorkflowState.EXECUTION_COMPLETED: WorkflowEvent.REPORT_PUBLISHED,
        WorkflowState.FAILURE_ANALYZED: WorkflowEvent.REPORT_PUBLISHED,
    }
    return mapping.get(state)
