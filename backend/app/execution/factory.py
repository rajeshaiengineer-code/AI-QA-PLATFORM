"""Runner factory — stub (default) or local Playwright."""

from __future__ import annotations

from typing import Protocol, Sequence, Any, Dict, Optional, List

from app.execution.playwright_runner import PlaywrightLocalRunner
from app.execution.stub_runner import CaseRunResult, RunnableCase, StubTestRunner


class TestRunner(Protocol):
    name: str

    def run(
        self,
        cases: Sequence[RunnableCase],
        *,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[CaseRunResult]:
        ...


def get_runner(name: Optional[str] = None) -> TestRunner:
    """Return a runner instance by name (``stub`` | ``playwright``)."""
    key = (name or "stub").strip().lower()
    if key in ("playwright", "pw", "browser"):
        return PlaywrightLocalRunner()
    return StubTestRunner()
