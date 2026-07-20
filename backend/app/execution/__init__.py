"""Execution engine package — stub + local Playwright runners."""

from app.execution.factory import get_runner
from app.execution.playwright_runner import PlaywrightLocalRunner, collect_playwright_files
from app.execution.stub_runner import CaseRunResult, StubTestRunner

__all__ = [
    "CaseRunResult",
    "StubTestRunner",
    "PlaywrightLocalRunner",
    "collect_playwright_files",
    "get_runner",
]
