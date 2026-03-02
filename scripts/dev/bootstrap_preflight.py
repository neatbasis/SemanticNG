#!/usr/bin/env python3
"""Fail-fast bootstrap preflight checks for local developer setup."""

from __future__ import annotations

import importlib.util
import re
import shutil
import sys
from pathlib import Path


def _read_requires_python(pyproject_path: Path) -> str:
    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r"^requires-python\s*=\s*[\"']([^\"']+)[\"']", content, flags=re.MULTILINE)
    if not match:
        raise ValueError(f"Unable to find requires-python in {pyproject_path}")
    return match.group(1)


def _parse_lower_bound(specifier: str) -> tuple[int, int, int]:
    match = re.search(r">=\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?", specifier)
    if not match:
        raise ValueError(f"Unable to parse lower-bound from requires-python: {specifier!r}")

    major = int(match.group(1))
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    return (major, minor, patch)


def _version_label(version: tuple[int, int, int]) -> str:
    major, minor, patch = version
    if patch:
        return f"{major}.{minor}.{patch}"
    return f"{major}.{minor}"


def _check_python_version(pyproject_path: Path) -> str | None:
    specifier = _read_requires_python(pyproject_path)
    lower_bound = _parse_lower_bound(specifier)
    current = sys.version_info[:3]
    if current < lower_bound:
        minimum = _version_label(lower_bound)
        found = _version_label((current[0], current[1], current[2]))
        return (
            f"python {found} is below required {minimum}. "
            f"Fix: use Python {minimum}+ (e.g. pyenv local {minimum})."
        )
    return None


def _check_precommit_executable() -> str | None:
    if shutil.which("pre-commit"):
        return None
    return "pre-commit executable not found. Fix: python -m pip install pre-commit"


def _check_editable_import() -> str | None:
    if importlib.util.find_spec("semanticng") is not None:
        return None
    return "semanticng import not found. Fix: python -m pip install -e \".[test]\""


def run_preflight(repo_root: Path) -> list[str]:
    pyproject_path = repo_root / "pyproject.toml"
    failures: list[str] = []

    for check in (
        lambda: _check_python_version(pyproject_path),
        _check_precommit_executable,
        _check_editable_import,
    ):
        failure = check()
        if failure:
            failures.append(failure)
    return failures


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    failures = run_preflight(repo_root)
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print("OK: bootstrap preflight checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
