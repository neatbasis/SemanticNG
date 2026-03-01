#!/usr/bin/env python3
"""Fail CI when pre-commit hook dependency and Python-version parity drifts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_MYPY_PACKAGES = (
    "pydantic",
    "pytest",
    "gherkin-official",
    "typing-extensions",
)
REQUIRED_HOOK_LANGUAGE_VERSION = "python3.11"


class ParityError(RuntimeError):
    """Raised when expected hook parity constraints are not met."""


def _normalize_package_name(requirement: str) -> str:
    base = re.split(r"[<>=!~\[]", requirement, maxsplit=1)[0]
    return base.strip().lower().replace("_", "-")


def _extract_hook_block(config_lines: list[str], hook_id: str) -> list[str]:
    hook_pattern = re.compile(rf"^(\s*)-\s+id:\s+{re.escape(hook_id)}\s*$")
    start_index = -1
    hook_indent = ""

    for idx, line in enumerate(config_lines):
        match = hook_pattern.match(line)
        if match:
            start_index = idx
            hook_indent = match.group(1)
            break

    if start_index < 0:
        raise ParityError(f"Could not find hook id '{hook_id}' in .pre-commit-config.yaml.")

    block: list[str] = []
    for line in config_lines[start_index + 1 :]:
        if re.match(rf"^{re.escape(hook_indent)}-\s+id:\s+", line):
            break
        block.append(line)

    return block


def _extract_hook_language_version(hook_block: list[str], hook_id: str) -> str:
    for line in hook_block:
        stripped = line.strip()
        if stripped.startswith("language_version:"):
            return stripped.split(":", maxsplit=1)[1].strip()
    raise ParityError(f"Hook '{hook_id}' is missing 'language_version'.")


def _extract_additional_dependencies(hook_block: list[str]) -> list[str]:
    deps: list[str] = []
    in_dep_list = False

    for line in hook_block:
        stripped = line.strip()
        if stripped.startswith("additional_dependencies:"):
            in_dep_list = True
            continue

        if in_dep_list:
            if stripped.startswith("-"):
                deps.append(stripped.removeprefix("-").strip())
                continue
            if stripped:
                break

    return deps


def main() -> int:
    config_lines = Path(".pre-commit-config.yaml").read_text(encoding="utf-8").splitlines()

    mypy_block = _extract_hook_block(config_lines, "mypy")
    mypy_deps = {_normalize_package_name(dep) for dep in _extract_additional_dependencies(mypy_block)}
    missing = [pkg for pkg in REQUIRED_MYPY_PACKAGES if pkg not in mypy_deps]
    if missing:
        print("Pre-commit parity failure: missing mypy additional_dependencies.")
        print("  expected packages:")
        for package in REQUIRED_MYPY_PACKAGES:
            print(f"    - {package}")
        print("  missing packages:")
        for package in missing:
            print(f"    - {package}")
        return 1

    for hook_id in ("mypy", "ruff", "ruff-format"):
        hook_block = _extract_hook_block(config_lines, hook_id)
        language_version = _extract_hook_language_version(hook_block, hook_id)
        if language_version != REQUIRED_HOOK_LANGUAGE_VERSION:
            print("Pre-commit parity failure: language_version mismatch.")
            print(f"  hook: {hook_id}")
            print(f"  expected: {REQUIRED_HOOK_LANGUAGE_VERSION}")
            print(f"  found: {language_version}")
            return 1

    print(
        "Pre-commit parity in sync: "
        f"mypy deps={', '.join(REQUIRED_MYPY_PACKAGES)}; "
        f"language_version={REQUIRED_HOOK_LANGUAGE_VERSION}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
