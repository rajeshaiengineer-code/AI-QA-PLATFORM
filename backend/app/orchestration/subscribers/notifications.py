"""
EventBus subscriber: notify on workflow COMPLETED / FAILED.

Registers handlers for WORKFLOW_COMPLETED and WORKFLOW_FAILED when
NOTIFICATIONS_WORKFLOW_HOOK is enabled. Uses NOTIFICATIONS_DEFAULT_RECIPIENT
and NOTIFICATIONS_DEFAULT_CHANNEL from settings.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.models.enums import NotificationChannel
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.events.models import DomainEvent
from app.orchestration.runtime import get_event_bus
from app.services.notifications import NotificationService

logger = get_logger(__name__)

_registered = False


def _parse_channel(value: str) -> NotificationChannel:
    try:
        return NotificationChannel(value.lower().strip())
    except ValueError:
        return NotificationChannel.EMAIL


async def handle_workflow_lifecycle(
    event: DomainEvent,
    *,
    settings: Optional[Settings] = None,
    session_factory: Optional[Callable[[], Awaitable[AsyncSession]]] = None,
) -> None:
    """
    Send a notification when a workflow reaches a terminal lifecycle event.

    ``session_factory`` is an async context manager factory
    (defaults to ``async_session_factory``).
    """
    cfg = settings or get_settings()
    if not cfg.NOTIFICATIONS_WORKFLOW_HOOK:
        return

    recipient = cfg.NOTIFICATIONS_DEFAULT_RECIPIENT
    if not recipient:
        logger.debug(
            "Skipping workflow notification — NOTIFICATIONS_DEFAULT_RECIPIENT unset",
            extra_fields={"event_type": event.event_type.value},
        )
        return

    channel = _parse_channel(cfg.NOTIFICATIONS_DEFAULT_CHANNEL)
    run_id: Optional[UUID] = event.correlation_id
    payload_run = event.payload.get("workflow_run_id") or event.payload.get("run_id")
    if payload_run:
        try:
            run_id = UUID(str(payload_run))
        except (TypeError, ValueError):
            pass

    status_label = (
        "COMPLETED"
        if event.event_type == WorkflowEvent.WORKFLOW_COMPLETED
        else "FAILED"
    )
    subject = f"Workflow {status_label}"
    story_part = f" story={event.story_id}" if event.story_id else ""
    body = (
        f"Workflow run {run_id or event.correlation_id} {status_label.lower()}."
        f"{story_part}\n"
        f"Event: {event.event_type.value}"
    )

    factory = session_factory or async_session_factory
    async with factory() as session:
        service = NotificationService(session, settings=cfg)
        result = await service.send_raw(
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            metadata={
                "source": "workflow_event_bus",
                "event_type": event.event_type.value,
                "event_id": str(event.event_id),
            },
            workflow_run_id=run_id,
            story_id=event.story_id,
            organization_id=event.organization_id,
            project_id=event.project_id,
        )
        logger.info(
            "Workflow lifecycle notification dispatched",
            extra_fields={
                "event_type": event.event_type.value,
                "success": result.success,
                "channel": channel.value,
                "notification_id": str(result.notification_id)
                if result.notification_id
                else None,
            },
        )


async def _handle_workflow_lifecycle(event: DomainEvent) -> None:
    await handle_workflow_lifecycle(event)


def register_notification_subscribers(
    settings: Optional[Settings] = None,
) -> None:
    """
    Subscribe notification handlers on the process EventBus (idempotent).

    Called from application lifespan when NOTIFICATIONS_WORKFLOW_HOOK is True.
    """
    global _registered
    cfg = settings or get_settings()
    if not cfg.NOTIFICATIONS_WORKFLOW_HOOK:
        return
    if _registered:
        return

    bus = get_event_bus()
    bus.subscribe(WorkflowEvent.WORKFLOW_COMPLETED, _handle_workflow_lifecycle)
    bus.subscribe(WorkflowEvent.WORKFLOW_FAILED, _handle_workflow_lifecycle)
    _registered = True
    logger.info("Notification EventBus subscribers registered")


def reset_notification_subscribers_for_tests() -> None:
    """Allow tests to re-register after clearing the bus."""
    global _registered
    _registered = False
