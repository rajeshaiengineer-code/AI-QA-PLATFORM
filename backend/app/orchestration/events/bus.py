"""In-process EventBus (at-least-once within a process)."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Awaitable, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4

from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.events.models import DomainEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[DomainEvent], Union[None, Awaitable[None]]]


class Subscription:
    def __init__(self, subscription_id: UUID, event_type: WorkflowEvent) -> None:
        self.id = subscription_id
        self.event_type = event_type


class InProcessEventBus:
    """Simple async-capable pub/sub for development and MVP."""

    def __init__(self) -> None:
        self._handlers: Dict[WorkflowEvent, Dict[UUID, EventHandler]] = defaultdict(
            dict
        )

    def subscribe(
        self,
        event_type: WorkflowEvent,
        handler: EventHandler,
    ) -> Subscription:
        sub_id = uuid4()
        self._handlers[event_type][sub_id] = handler
        return Subscription(sub_id, event_type)

    def unsubscribe(self, subscription: Subscription) -> None:
        self._handlers.get(subscription.event_type, {}).pop(subscription.id, None)

    async def publish(self, event: DomainEvent) -> None:
        handlers = list(self._handlers.get(event.event_type, {}).values())
        # Also deliver to wildcard-style subscribers registered on WORKFLOW_COMPLETED
        # for audit — handlers are per event type only.
        for handler in handlers:
            try:
                result = handler(event)
                if result is not None and hasattr(result, "__await__"):
                    await result  # type: ignore[misc]
            except Exception:  # noqa: BLE001 — bus must not crash publishers
                logger.exception(
                    "Event handler failed for %s",
                    event.event_type.value,
                )

    async def publish_batch(self, events: List[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)

    def clear(self) -> None:
        self._handlers.clear()
