"""
Stub / local test runner for MVP execution.

Records deterministic pass/fail without launching Playwright or any browser.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Sequence
from uuid import UUID

from app.models.enums import ExecutionStatus


class RunnableCase(Protocol):
    """Minimal surface required from a test case for the stub runner."""

    id: UUID
    title: str


@dataclass(frozen=True)
class CaseRunResult:
    """Outcome of running a single case in the stub runner."""

    test_case_id: UUID
    status: ExecutionStatus
    duration_ms: int
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    evidence_url: Optional[str] = None


class StubTestRunner:
    """
    Simulated local runner.

    Failure rules (first match wins):
      1. ``test_case.id`` in ``config["force_fail_test_case_ids"]``
      2. title contains ``"fail"`` (case-insensitive)
      3. otherwise PASSED
    """

    name: str = "stub"

    def run(
        self,
        cases: Sequence[RunnableCase],
        *,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[CaseRunResult]:
        cfg = config or {}
        force_fail = {
            UUID(str(x)) for x in (cfg.get("force_fail_test_case_ids") or [])
        }
        results: List[CaseRunResult] = []
        for case in cases:
            duration_ms = 40 + (case.id.int % 160)
            if case.id in force_fail or "fail" in (case.title or "").lower():
                results.append(
                    CaseRunResult(
                        test_case_id=case.id,
                        status=ExecutionStatus.FAILED,
                        duration_ms=duration_ms,
                        error_message=f"Stub failure: {case.title}",
                        stack_trace=(
                            f"StubTestRunnerError: simulated failure for "
                            f"test_case={case.id}"
                        ),
                        evidence_url=f"stub://evidence/{case.id}",
                    )
                )
            else:
                results.append(
                    CaseRunResult(
                        test_case_id=case.id,
                        status=ExecutionStatus.PASSED,
                        duration_ms=duration_ms,
                        evidence_url=f"stub://evidence/{case.id}",
                    )
                )
        return results
