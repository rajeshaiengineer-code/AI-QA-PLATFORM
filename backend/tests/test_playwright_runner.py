"""Unit tests for Playwright local runner + factory."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.execution.factory import get_runner
from app.execution.playwright_runner import (
    PlaywrightLocalRunner,
    collect_playwright_files,
)
from app.execution.stub_runner import StubTestRunner
from app.models.enums import ExecutionStatus


class _FakeCase:
    def __init__(self, title: str) -> None:
        self.id = uuid4()
        self.title = title


class _FakeArtifact:
    def __init__(self) -> None:
        self.specs = [
            {
                "path": "tests/login.spec.ts",
                "content": "import { test } from '@playwright/test';\ntest('x', async () => {});",
            }
        ]
        self.page_objects = [{"path": "pages/Login.ts", "content": "export {}"}]
        self.locators = None
        self.fixtures = None
        self.utilities = None
        self.assertions = None
        self.hooks = None


def test_get_runner_defaults_to_stub():
    assert isinstance(get_runner(None), StubTestRunner)
    assert isinstance(get_runner("stub"), StubTestRunner)
    assert isinstance(get_runner("playwright"), PlaywrightLocalRunner)


def test_collect_playwright_files():
    files = collect_playwright_files(_FakeArtifact())
    paths = {f["path"] for f in files}
    assert "tests/login.spec.ts" in paths
    assert "pages/Login.ts" in paths


def test_playwright_runner_errors_without_files():
    runner = PlaywrightLocalRunner()
    case = _FakeCase("Login works")
    results = runner.run([case], config={})
    assert len(results) == 1
    assert results[0].status == ExecutionStatus.ERROR
    assert "specs" in (results[0].error_message or "").lower()


def test_playwright_runner_maps_json_results(tmp_path: Path, monkeypatch):
    runner = PlaywrightLocalRunner(npx_bin="npx")
    case_pass = _FakeCase("Login succeeds")
    case_fail = _FakeCase("Login fails")

    work = tmp_path / "run"
    work.mkdir()
    payload = {
        "suites": [
            {
                "title": "login.spec.ts",
                "specs": [
                    {
                        "title": "Login succeeds",
                        "tests": [
                            {
                                "results": [
                                    {"status": "passed", "duration": 120, "errors": []}
                                ]
                            }
                        ],
                    },
                    {
                        "title": "Login fails",
                        "tests": [
                            {
                                "results": [
                                    {
                                        "status": "failed",
                                        "duration": 80,
                                        "errors": [{"message": "Expected visible"}],
                                    }
                                ]
                            }
                        ],
                    },
                ],
                "suites": [],
            }
        ]
    }
    (work / "results.json").write_text(json.dumps(payload), encoding="utf-8")

    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "some stderr"

    def _fake_invoke(self, root, cfg):  # noqa: ANN001
        return _Proc()

    monkeypatch.setattr(PlaywrightLocalRunner, "_invoke_playwright", _fake_invoke)

    results = runner.run(
        [case_pass, case_fail],
        config={
            "playwright_files": [
                {"path": "tests/a.spec.ts", "content": "test('x', async () => {});"}
            ],
            "playwright_workdir": str(work),
            "playwright_keep_workdir": True,
        },
    )
    assert results[0].status == ExecutionStatus.PASSED
    assert results[1].status == ExecutionStatus.FAILED
    assert "Expected visible" in (results[1].error_message or "")
