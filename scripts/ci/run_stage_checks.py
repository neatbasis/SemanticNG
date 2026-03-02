#!/usr/bin/env python3
"""Run deterministic QA stages with budgets and actionable failure output."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass

FILE_RE = re.compile(r"(?P<path>[A-Za-z0-9_./-]+\.(?:py|pyi|yaml|yml|toml|json|md|txt))(?:[:(]|\s)")


@dataclass(frozen=True)
class CommandSpec:
    command: str
    timeout_seconds: int


STAGES: dict[str, list[CommandSpec]] = {
    "qa-commit": [
        CommandSpec("ruff check --fix src/core src/state_renormalization", 20),
        CommandSpec("mypy --config-file=pyproject.toml src/state_renormalization src/core", 40),
    ],
    "qa-push": [
        CommandSpec("ruff check --fix src tests", 45),
        CommandSpec("ruff format --check src tests", 35),
        CommandSpec("mypy --config-file=pyproject.toml src/state_renormalization src/core", 60),
        CommandSpec(
            "pytest -q tests/test_engine_pending_obligation.py tests/test_invariants.py tests/test_contracts_decision_effect_shape.py",
            80,
        ),
    ],
    "qa-ci": [
        CommandSpec("python .github/scripts/check_no_regression_budget.py", 20),
        CommandSpec("pre-commit run --all-files", 180),
        CommandSpec("pytest --cov --cov-report=term-missing --cov-report=xml", 240),
        CommandSpec("mypy --config-file=pyproject.toml src tests", 240),
    ],
}


def _first_failing_files(output: str) -> list[str]:
    files: list[str] = []
    for match in FILE_RE.finditer(output):
        path = match.group("path")
        if path not in files:
            files.append(path)
        if len(files) >= 5:
            break
    return files


def _run_command(spec: CommandSpec) -> int:
    print(f"\n▶ Running: {spec.command}")
    print(f"   Timeout budget: {spec.timeout_seconds}s")
    started = time.monotonic()
    try:
        proc = subprocess.run(
            spec.command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=spec.timeout_seconds,
        )
    except subprocess.TimeoutExpired as err:
        elapsed = time.monotonic() - started
        print(err.stdout or "", end="")
        print(err.stderr or "", end="", file=sys.stderr)
        print(f"\n✖ Timeout after {elapsed:.1f}s (budget {spec.timeout_seconds}s)")
        print(f"Rerun command: {spec.command}")
        return 124

    elapsed = time.monotonic() - started
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)

    if proc.returncode != 0:
        print(f"\n✖ Failed in {elapsed:.1f}s with exit code {proc.returncode}")
        print(f"Rerun command: {spec.command}")
        failing_files = _first_failing_files((proc.stdout or "") + "\n" + (proc.stderr or ""))
        if failing_files:
            print(f"First failing files: {', '.join(failing_files)}")
        else:
            print("First failing files: none detected from output")
    else:
        print(f"✔ Passed in {elapsed:.1f}s")

    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=tuple(STAGES.keys()))
    args = parser.parse_args()

    print(f"QA stage: {args.stage}")
    for spec in STAGES[args.stage]:
        code = _run_command(spec)
        if code != 0:
            return code

    print(f"\nStage {args.stage} passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
