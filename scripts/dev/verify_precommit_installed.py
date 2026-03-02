#!/usr/bin/env python3
"""Fail-fast verifier for required local pre-commit hooks."""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path

REQUIRED_HOOKS = ("pre-commit", "pre-push")
PRECOMMIT_MARKERS = (
    "pre-commit",
    "from pre_commit",
)


def _git_config_hooks_path(repo_root: Path, *, local_only: bool) -> str | None:
    command = ["git", "config"]
    if local_only:
        command.append("--local")
    command.extend(["--get", "core.hooksPath"])

    result = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    hooks_path = result.stdout.strip()
    return hooks_path or None


def _resolve_hooks_dir(repo_root: Path) -> Path:
    hooks_path = _git_config_hooks_path(repo_root, local_only=True)
    if hooks_path is None:
        hooks_path = _git_config_hooks_path(repo_root, local_only=False)

    if hooks_path is None:
        return repo_root / ".git" / "hooks"

    configured_path = Path(hooks_path)
    if configured_path.is_absolute():
        return configured_path
    return repo_root / configured_path


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
    hooks_dir = _resolve_hooks_dir(repo_root)

    failures: list[str] = []
    for hook_name in REQUIRED_HOOKS:
        hook_issue = _validate_hook(hooks_dir / hook_name)
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
            f"  python scripts/dev/verify_precommit_installed.py\n"
            f"\nResolved hooks directory: {hooks_dir}",
            file=sys.stderr,
        )
        return 1

    print("OK: pre-commit and pre-push hooks are installed and managed by pre-commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
