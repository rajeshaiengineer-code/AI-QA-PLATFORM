"""AgentRegistry — resolve agents by triggering event type."""

from typing import Dict, List, Optional

from app.orchestration.agents.base import Agent
from app.orchestration.events.enums import WorkflowEvent


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: Dict[str, Agent] = {}
        self._by_event: Dict[WorkflowEvent, List[str]] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.name] = agent
        for event in agent.supported_events:
            self._by_event.setdefault(event, []).append(agent.name)

    def resolve(self, event_type: WorkflowEvent) -> List[Agent]:
        names = self._by_event.get(event_type, [])
        return [self._agents[name] for name in names if name in self._agents]

    def get(self, name: str) -> Optional[Agent]:
        return self._agents.get(name)

    def clear(self) -> None:
        self._agents.clear()
        self._by_event.clear()
