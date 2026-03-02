#!/usr/bin/env python3
"""Fail-fast verifier for required local pre-commit hooks."""

from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_HOOKS = ("pre-commit", "pre-push")
PRECOMMIT_MARKERS = (
    "pre-commit",
    "from pre_commit",
)


def _hook_path(repo_root: Path, hook_name: str) -> Path:
    return repo_root / ".git" / "hooks" / hook_name


def _validate_hook(path: Path) -> str | None:
    if not path.exists():
        return f"Missing required hook: {path}"

    content = path.read_text(encoding="utf-8", errors="ignore")
    if not any(marker in content for marker in PRECOMMIT_MARKERS):
        return (
            f"Hook exists but does not appear to be managed by pre-commit: {path}. "
            "Expected hook content to reference pre-commit."
        )

    return None


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]

    failures: list[str] = []
    for hook_name in REQUIRED_HOOKS:
        hook_issue = _validate_hook(_hook_path(repo_root, hook_name))
        if hook_issue:
            failures.append(hook_issue)

    if failures:
        print("ERROR: Required git hooks are not correctly installed.", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        print(
            "\nRemediation:\n"
            "  pre-commit install --hook-type pre-commit --hook-type pre-push\n"
            "  pre-commit install-hooks\n"
            "  python scripts/dev/verify_precommit_installed.py",
            file=sys.stderr,
        )
        return 1

    print("OK: pre-commit and pre-push hooks are installed and managed by pre-commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
