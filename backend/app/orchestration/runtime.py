"""Process-wide EventBus and AgentRegistry for workflow orchestration."""

from app.orchestration.agents.registry import AgentRegistry
from app.orchestration.events.bus import InProcessEventBus

_event_bus = InProcessEventBus()
_agent_registry = AgentRegistry()


def get_event_bus() -> InProcessEventBus:
    return _event_bus


def get_agent_registry() -> AgentRegistry:
    return _agent_registry


def register_builtin_agents() -> None:
    """Register shipped workflow agents (idempotent)."""
    from app.orchestration.agents.bdd_generator import BddGeneratorAgent
    from app.orchestration.agents.bug_creation import BugCreationAgent
    from app.orchestration.agents.execution import ExecutionAgent
    from app.orchestration.agents.failure_analysis import FailureAnalysisAgent
    from app.orchestration.agents.github_pr import GitHubPRAgent
    from app.orchestration.agents.playwright_generator import PlaywrightGeneratorAgent
    from app.orchestration.agents.story_analyzer import StoryAnalyzerAgent
    from app.orchestration.agents.test_case_generator import TestCaseGeneratorAgent

    if _agent_registry.get(StoryAnalyzerAgent.name) is None:
        _agent_registry.register(StoryAnalyzerAgent())
    if _agent_registry.get(TestCaseGeneratorAgent.name) is None:
        _agent_registry.register(TestCaseGeneratorAgent())
    if _agent_registry.get(BddGeneratorAgent.name) is None:
        _agent_registry.register(BddGeneratorAgent())
    if _agent_registry.get(PlaywrightGeneratorAgent.name) is None:
        _agent_registry.register(PlaywrightGeneratorAgent())
    if _agent_registry.get(GitHubPRAgent.name) is None:
        _agent_registry.register(GitHubPRAgent())
    if _agent_registry.get(ExecutionAgent.name) is None:
        _agent_registry.register(ExecutionAgent())
    if _agent_registry.get(FailureAnalysisAgent.name) is None:
        _agent_registry.register(FailureAnalysisAgent())
    if _agent_registry.get(BugCreationAgent.name) is None:
        _agent_registry.register(BugCreationAgent())


def get_workflow_engine(session):
    from app.orchestration.engine.engine import WorkflowEngine

    return WorkflowEngine(
        session=session,
        bus=_event_bus,
        agent_registry=_agent_registry,
    )
