"""
QA Approval Service

Business orchestration for reviewing, editing, approving, and rejecting
test cases, with version history and optional workflow gate advancement.
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.enums import TestCaseStatus
from app.models.test_case import TestCase
from app.models.test_case_version import TestCaseVersion
from app.models.workflow_run import WorkflowRun
from app.orchestration.runtime import get_workflow_engine
from app.orchestration.state.enums import WorkflowState
from app.repositories.story import StoryRepository
from app.repositories.test_case import TestCaseRepository
from app.repositories.test_case_version import TestCaseVersionRepository
from app.schemas.base import PaginatedResponse
from app.schemas.test_case import (
    TestCaseApproveAllResponse,
    TestCaseDecisionResponse,
    TestCaseResponse,
    TestCaseUpdate,
    TestCaseVersionResponse,
)


class QAApprovalService:
    """Service layer for QA review of test cases."""

    # Statuses eligible for approve-all / individual approve.
    _APPROVABLE = {
        TestCaseStatus.DRAFT.value,
        TestCaseStatus.PENDING_REVIEW.value,
        TestCaseStatus.REJECTED.value,
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.story_repo = StoryRepository(session)
        self.test_case_repo = TestCaseRepository(session)
        self.version_repo = TestCaseVersionRepository(session)

    async def get_test_case(self, test_case_id: UUID) -> TestCaseResponse:
        """Fetch a single test case by id."""
        entity = await self._require_test_case(test_case_id)
        return TestCaseResponse.model_validate(entity)

    async def list_pending_review(
        self,
        story_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[TestCaseResponse]:
        """List test cases pending QA review for a story."""
        await self._require_story(story_id)
        offset = (page - 1) * page_size
        rows, total = await self.test_case_repo.list_for_story(
            story_id,
            offset=offset,
            limit=page_size,
            status=TestCaseStatus.PENDING_REVIEW,
        )
        items = [TestCaseResponse.model_validate(row) for row in rows]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_test_case(
        self,
        test_case_id: UUID,
        payload: TestCaseUpdate,
    ) -> TestCaseResponse:
        """
        Edit a test case, snapshotting the previous state first.

        Content edits on approved/rejected cases reset status to pending_review.
        """
        entity = await self._require_test_case(test_case_id)
        data = payload.model_dump(exclude_unset=True)
        change_reason = data.pop("change_reason", None)

        if not data:
            raise BadRequestException("No fields provided to update")

        await self._snapshot(entity, change_reason=change_reason)

        if "steps" in data and payload.steps is not None:
            data["steps"] = [step.model_dump() for step in payload.steps]

        if "category" in data and data["category"] is not None:
            cat = data["category"]
            data["category"] = cat.value if hasattr(cat, "value") else cat

        for field, value in data.items():
            setattr(entity, field, value)

        if entity.status in (
            TestCaseStatus.APPROVED.value,
            TestCaseStatus.REJECTED.value,
        ):
            entity.status = TestCaseStatus.PENDING_REVIEW.value
            entity.rejection_reason = None

        entity.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        column_keys = [column.key for column in entity.__table__.columns]
        await self.session.refresh(entity, attribute_names=column_keys)
        return TestCaseResponse.model_validate(entity)

    async def approve_test_case(
        self,
        test_case_id: UUID,
        *,
        note: Optional[str] = None,
    ) -> TestCaseDecisionResponse:
        """Approve a single test case; advance workflow when all are approved."""
        entity = await self._require_test_case(test_case_id)
        if entity.status == TestCaseStatus.APPROVED.value:
            raise BadRequestException("Test case is already approved")

        await self._snapshot(
            entity,
            change_reason=note or "Approved",
        )
        entity.status = TestCaseStatus.APPROVED.value
        entity.rejection_reason = None
        entity.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        column_keys = [column.key for column in entity.__table__.columns]
        await self.session.refresh(entity, attribute_names=column_keys)

        advanced, run_id, message = await self._maybe_advance_workflow(entity.story_id)
        return TestCaseDecisionResponse(
            test_case=TestCaseResponse.model_validate(entity),
            workflow_advanced=advanced,
            workflow_run_id=run_id,
            message=message,
        )

    async def reject_test_case(
        self,
        test_case_id: UUID,
        *,
        reason: Optional[str] = None,
    ) -> TestCaseDecisionResponse:
        """Reject a single test case (does not advance the workflow gate)."""
        entity = await self._require_test_case(test_case_id)
        if entity.status == TestCaseStatus.REJECTED.value:
            raise BadRequestException("Test case is already rejected")

        await self._snapshot(
            entity,
            change_reason=reason or "Rejected",
        )
        entity.status = TestCaseStatus.REJECTED.value
        entity.rejection_reason = reason
        entity.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        column_keys = [column.key for column in entity.__table__.columns]
        await self.session.refresh(entity, attribute_names=column_keys)

        return TestCaseDecisionResponse(
            test_case=TestCaseResponse.model_validate(entity),
            workflow_advanced=False,
            workflow_run_id=None,
            message="Test case rejected",
        )

    async def approve_all_for_story(
        self,
        story_id: UUID,
    ) -> TestCaseApproveAllResponse:
        """
        Approve all draft / pending_review / rejected test cases for a story.

        Already-approved cases are left unchanged. When every case is approved,
        optionally advances a workflow run stuck at test_cases_generated.
        """
        await self._require_story(story_id)
        cases = await self.test_case_repo.list_all_for_story(story_id)
        if not cases:
            raise BadRequestException("No test cases found for this story")

        approved: List[TestCase] = []
        for entity in cases:
            if entity.status == TestCaseStatus.APPROVED.value:
                continue
            if entity.status not in self._APPROVABLE:
                continue
            await self._snapshot(entity, change_reason="Approved via approve-all")
            entity.status = TestCaseStatus.APPROVED.value
            entity.rejection_reason = None
            entity.updated_at = datetime.now(timezone.utc)
            approved.append(entity)

        await self.session.flush()
        for entity in approved:
            column_keys = [column.key for column in entity.__table__.columns]
            await self.session.refresh(entity, attribute_names=column_keys)

        advanced, run_id, message = await self._maybe_advance_workflow(story_id)
        items = [TestCaseResponse.model_validate(e) for e in approved]
        if not message:
            message = (
                f"Approved {len(items)} test case(s)"
                if items
                else "All test cases were already approved"
            )
        return TestCaseApproveAllResponse(
            story_id=story_id,
            approved_count=len(items),
            items=items,
            workflow_advanced=advanced,
            workflow_run_id=run_id,
            message=message,
        )

    async def list_versions(
        self,
        test_case_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[TestCaseVersionResponse]:
        """List version history for a test case (newest first)."""
        await self._require_test_case(test_case_id)
        offset = (page - 1) * page_size
        rows, total = await self.version_repo.list_for_test_case(
            test_case_id,
            offset=offset,
            limit=page_size,
        )
        items = [TestCaseVersionResponse.model_validate(row) for row in rows]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def _snapshot(
        self,
        entity: TestCase,
        *,
        change_reason: Optional[str] = None,
    ) -> TestCaseVersion:
        """Persist a point-in-time copy of the current test case content."""
        next_number = await self.version_repo.max_version_number(entity.id) + 1
        now = datetime.now(timezone.utc)
        snapshot = TestCaseVersion(
            test_case_id=entity.id,
            version_number=next_number,
            title=entity.title,
            description=entity.description,
            preconditions=entity.preconditions,
            steps=entity.steps,
            expected_result=entity.expected_result,
            priority=entity.priority,
            is_automated=entity.is_automated,
            category=entity.category,
            tags=entity.tags,
            status=entity.status,
            change_reason=change_reason,
            created_at=now,
            updated_at=now,
        )
        return await self.version_repo.add(snapshot)

    async def _maybe_advance_workflow(
        self,
        story_id: UUID,
    ) -> Tuple[bool, Optional[UUID], Optional[str]]:
        """
        If every test case for the story is approved and a workflow run is at
        test_cases_generated, call WorkflowEngine.approve().

        Returns (advanced, run_id, message). Failures / missing runs are soft.
        """
        total = await self.test_case_repo.count_for_story(story_id)
        if total == 0:
            return False, None, None

        approved_count = await self.test_case_repo.count_by_status(
            story_id,
            TestCaseStatus.APPROVED,
        )
        if approved_count < total:
            remaining = total - approved_count
            return (
                False,
                None,
                f"Approved; {remaining} test case(s) still awaiting approval",
            )

        run = await self._latest_workflow_run(story_id)
        if run is None:
            return (
                False,
                None,
                "All test cases approved; no workflow run to advance",
            )

        if run.state != WorkflowState.TEST_CASES_GENERATED.value:
            return (
                False,
                run.id,
                (
                    "All test cases approved; workflow run is in state "
                    f"'{run.state}' (expected test_cases_generated)"
                ),
            )

        engine = get_workflow_engine(self.session)
        await engine.approve(
            run.id,
            approved=True,
            reason="All test cases approved",
        )
        return True, run.id, "All test cases approved; workflow advanced to qa_approved"

    async def _latest_workflow_run(
        self,
        story_id: UUID,
    ) -> Optional[WorkflowRun]:
        stmt = (
            select(WorkflowRun)
            .options(noload(WorkflowRun.logs))
            .where(
                WorkflowRun.story_id == story_id,
                WorkflowRun.is_deleted.is_(False),
            )
            .order_by(WorkflowRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _require_test_case(self, test_case_id: UUID) -> TestCase:
        entity = await self.test_case_repo.get_by_id(test_case_id)
        if entity is None:
            raise NotFoundException("TestCase", str(test_case_id))
        return entity

    async def _require_story(self, story_id: UUID) -> None:
        story = await self.story_repo.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))
