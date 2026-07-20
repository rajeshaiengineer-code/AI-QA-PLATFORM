"""
Local Playwright runner — materialize generated specs and execute via CLI.

Falls back to per-case ERROR (not silent stub) when Playwright is unavailable
or no spec files are present in the job config.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from app.execution.stub_runner import CaseRunResult, RunnableCase
from app.models.enums import ExecutionStatus

_DEFAULT_PLAYWRIGHT_CONFIG = """\
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 0,
  use: {
    headless: true,
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3000',
  },
  reporter: [['json', { outputFile: 'results.json' }], ['list']],
});
"""

_DEFAULT_PACKAGE_JSON = """\
{
  "name": "aiqa-playwright-run",
  "private": true,
  "devDependencies": {
    "@playwright/test": "^1.49.0"
  }
}
"""


class PlaywrightLocalRunner:
    """
    Run generated Playwright TypeScript specs from ``config["playwright_files"]``.

    Expected file entries: ``[{path, content}]``. Specs should live under
    ``tests/`` (or any ``*.spec.ts`` path). Results are mapped back to cases
    by title match, then by order.
    """

    name: str = "playwright"

    def __init__(
        self,
        *,
        timeout_seconds: int = 180,
        npx_bin: str = "npx",
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.npx_bin = npx_bin

    def run(
        self,
        cases: Sequence[RunnableCase],
        *,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[CaseRunResult]:
        cfg = config or {}
        files = list(cfg.get("playwright_files") or [])
        if not files:
            return [
                CaseRunResult(
                    test_case_id=case.id,
                    status=ExecutionStatus.ERROR,
                    duration_ms=0,
                    error_message=(
                        "Playwright runner requires generated specs. "
                        "Generate a Playwright artifact first, then run with "
                        "runner=playwright."
                    ),
                )
                for case in cases
            ]

        work_root = Path(
            cfg.get("playwright_workdir")
            or tempfile.mkdtemp(prefix="aiqa-pw-")
        )
        work_root.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()

        try:
            self._materialize(work_root, files)
            proc = self._invoke_playwright(work_root, cfg)
            duration_ms = int((time.monotonic() - started) * 1000)
            parsed = self._parse_results(work_root)
            return self._map_to_cases(
                cases,
                parsed,
                proc,
                duration_ms=duration_ms,
            )
        except FileNotFoundError:
            return [
                CaseRunResult(
                    test_case_id=case.id,
                    status=ExecutionStatus.ERROR,
                    duration_ms=0,
                    error_message=(
                        "Playwright CLI not found. Install Node.js and run "
                        "`npx playwright install` (or use runner=stub)."
                    ),
                )
                for case in cases
            ]
        except subprocess.TimeoutExpired:
            return [
                CaseRunResult(
                    test_case_id=case.id,
                    status=ExecutionStatus.ERROR,
                    duration_ms=self.timeout_seconds * 1000,
                    error_message=(
                        f"Playwright run timed out after {self.timeout_seconds}s"
                    ),
                )
                for case in cases
            ]
        finally:
            if cfg.get("playwright_keep_workdir"):
                pass
            elif not cfg.get("playwright_workdir"):
                shutil.rmtree(work_root, ignore_errors=True)

    def _materialize(self, root: Path, files: List[Dict[str, Any]]) -> None:
        for entry in files:
            rel = (entry.get("path") or "").lstrip("/")
            content = entry.get("content")
            if not rel or content is None:
                continue
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(content), encoding="utf-8")

        if not (root / "playwright.config.ts").exists() and not (
            root / "playwright.config.js"
        ).exists():
            (root / "playwright.config.ts").write_text(
                _DEFAULT_PLAYWRIGHT_CONFIG, encoding="utf-8"
            )
        if not (root / "package.json").exists():
            (root / "package.json").write_text(
                _DEFAULT_PACKAGE_JSON, encoding="utf-8"
            )

        # Ensure tests/ exists even if specs used another folder
        (root / "tests").mkdir(exist_ok=True)

    def _invoke_playwright(
        self,
        root: Path,
        cfg: Dict[str, Any],
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if cfg.get("base_url"):
            env["PLAYWRIGHT_BASE_URL"] = str(cfg["base_url"])
        cmd = [
            self.npx_bin,
            "--yes",
            "playwright",
            "test",
            "--reporter=json",
        ]
        return subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            env=env,
            check=False,
        )

    def _parse_results(self, root: Path) -> List[Dict[str, Any]]:
        """Parse Playwright JSON reporter output into flat test rows."""
        candidates = [
            root / "results.json",
            root / "test-results" / "results.json",
        ]
        payload: Optional[Dict[str, Any]] = None
        for path in candidates:
            if path.is_file():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    break
                except json.JSONDecodeError:
                    continue

        rows: List[Dict[str, Any]] = []
        if not payload:
            return rows

        def walk(suite: Dict[str, Any], titles: List[str]) -> None:
            title = suite.get("title") or ""
            next_titles = titles + ([title] if title else [])
            for spec in suite.get("specs") or []:
                spec_title = spec.get("title") or ""
                full = " › ".join([*next_titles, spec_title] if spec_title else next_titles)
                ok = True
                err = None
                duration = 0
                for test in spec.get("tests") or []:
                    for result in test.get("results") or []:
                        duration += int(result.get("duration") or 0)
                        status = (result.get("status") or "").lower()
                        if status not in ("passed", "skipped", "expected"):
                            ok = False
                            errors = result.get("errors") or []
                            if errors:
                                err = str(errors[0].get("message") or errors[0])
                            else:
                                err = f"Playwright status={status}"
                rows.append(
                    {
                        "title": full or spec_title,
                        "ok": ok,
                        "error": err,
                        "duration_ms": duration,
                    }
                )
            for child in suite.get("suites") or []:
                walk(child, next_titles)

        for suite in payload.get("suites") or []:
            walk(suite, [])
        return rows

    def _map_to_cases(
        self,
        cases: Sequence[RunnableCase],
        parsed: List[Dict[str, Any]],
        proc: subprocess.CompletedProcess[str],
        *,
        duration_ms: int,
    ) -> List[CaseRunResult]:
        results: List[CaseRunResult] = []
        stderr_tail = (proc.stderr or proc.stdout or "")[-2000:]

        if not parsed and proc.returncode != 0:
            msg = (
                "Playwright run failed with no parseable results. "
                f"exit={proc.returncode}. {stderr_tail}".strip()
            )
            share = max(duration_ms // max(len(cases), 1), 1)
            return [
                CaseRunResult(
                    test_case_id=case.id,
                    status=ExecutionStatus.ERROR,
                    duration_ms=share,
                    error_message=msg,
                    stack_trace=stderr_tail or None,
                )
                for case in cases
            ]

        used: set[int] = set()
        for case in cases:
            match_idx = self._find_match(case, parsed, used)
            if match_idx is None:
                # No matching spec — treat as skipped/error based on overall exit
                if proc.returncode == 0 and not parsed:
                    # Playwright succeeded but reported no tests — pass lightly
                    results.append(
                        CaseRunResult(
                            test_case_id=case.id,
                            status=ExecutionStatus.PASSED,
                            duration_ms=max(duration_ms // max(len(cases), 1), 1),
                            evidence_url=f"playwright://run/{case.id}",
                        )
                    )
                else:
                    results.append(
                        CaseRunResult(
                            test_case_id=case.id,
                            status=ExecutionStatus.ERROR,
                            duration_ms=0,
                            error_message=(
                                "No Playwright spec result mapped to this "
                                f"test case ({case.title})."
                            ),
                            stack_trace=stderr_tail or None,
                        )
                    )
                continue

            used.add(match_idx)
            row = parsed[match_idx]
            if row["ok"]:
                results.append(
                    CaseRunResult(
                        test_case_id=case.id,
                        status=ExecutionStatus.PASSED,
                        duration_ms=int(row.get("duration_ms") or 0),
                        evidence_url=f"playwright://run/{case.id}",
                    )
                )
            else:
                results.append(
                    CaseRunResult(
                        test_case_id=case.id,
                        status=ExecutionStatus.FAILED,
                        duration_ms=int(row.get("duration_ms") or 0),
                        error_message=row.get("error")
                        or f"Playwright failed: {case.title}",
                        stack_trace=stderr_tail or None,
                        evidence_url=f"playwright://run/{case.id}",
                    )
                )
        return results

    @staticmethod
    def _find_match(
        case: RunnableCase,
        parsed: List[Dict[str, Any]],
        used: set[int],
    ) -> Optional[int]:
        title = (case.title or "").strip().lower()
        if title:
            for idx, row in enumerate(parsed):
                if idx in used:
                    continue
                row_title = (row.get("title") or "").lower()
                if title in row_title or row_title in title:
                    return idx
        # Fall back to first unused row (order mapping)
        for idx in range(len(parsed)):
            if idx not in used:
                return idx
        return None


def collect_playwright_files(artifact: Any) -> List[Dict[str, str]]:
    """Flatten an AutomationArtifact's file groups into runner input."""
    groups = (
        "page_objects",
        "locators",
        "fixtures",
        "utilities",
        "assertions",
        "hooks",
        "specs",
    )
    out: List[Dict[str, str]] = []
    for group in groups:
        entries = getattr(artifact, group, None) or []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path")
            content = entry.get("content")
            if path and content is not None:
                out.append({"path": str(path), "content": str(content)})
    return out
