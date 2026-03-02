#!/usr/bin/env python3
"""Validate Python/toolchain version declarations stay in sync across repo policy surfaces."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
PRECOMMIT = ROOT / ".pre-commit-config.yaml"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
ACTION_SETUP = ROOT / ".github" / "actions" / "python-test-setup" / "action.yml"
TOOLCHAIN_DOC = ROOT / "docs" / "dev_toolchain_parity.md"

TARGET_HOOKS = ("ruff", "ruff-format", "mypy")
TOOL_PINS = ("mypy", "ruff", "black", "isort")


class ToolchainParityError(RuntimeError):
    """Raised when repository toolchain declarations diverge."""


def _fail(message: str) -> int:
    print(f"Toolchain parity failure: {message}")
    return 1


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _canonical_python_minor(pyproject_text: str) -> str:
    match = re.search(r'^requires-python\s*=\s*"([^\"]+)"\s*$', pyproject_text, re.MULTILINE)
    if not match:
        raise ToolchainParityError("Unable to parse [project].requires-python from pyproject.toml")

    requires_python = match.group(1).replace(" ", "")
    lower = re.search(r">=([0-9]+\.[0-9]+)", requires_python)
    if not lower:
        raise ToolchainParityError(
            "requires-python must include a lower-bound in the form >=X.Y (for example '>=3.10')."
        )
    return lower.group(1)


def _extract_hook_block(lines: list[str], hook_id: str) -> list[str]:
    pattern = re.compile(rf"^(\s*)-\s+id:\s+{re.escape(hook_id)}\s*$")
    start = -1
    indent = ""

    for idx, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            start = idx
            indent = match.group(1)
            break

    if start < 0:
        raise ToolchainParityError(f"Missing pre-commit hook id '{hook_id}'.")

    block: list[str] = []
    for line in lines[start + 1 :]:
        if re.match(rf"^{re.escape(indent)}-\s+id:\s+", line):
            break
        block.append(line)

    return block


def _hook_language_version(block: list[str], hook_id: str) -> str:
    for line in block:
        stripped = line.strip()
        if stripped.startswith("language_version:"):
            return stripped.split(":", maxsplit=1)[1].strip()
    raise ToolchainParityError(f"Hook '{hook_id}' is missing language_version.")


def _read_workflow_python_versions(path: Path) -> list[str]:
    versions: list[str] = []
    lines = _read_text(path).splitlines()
    for idx, line in enumerate(lines):
        if "uses:" in line and "actions/setup-python@" in line:
            for probe in lines[idx + 1 : idx + 12]:
                stripped = probe.strip()
                if stripped.startswith("python-version:"):
                    value = stripped.split(":", maxsplit=1)[1].strip().strip("'\"")
                    versions.append(value)
                    break
    return versions


def _extract_test_extra_constraints(pyproject_text: str) -> dict[str, str]:
    match = re.search(
        r"^test\s*=\s*\[(?P<body>.*?)\]\s*$",
        pyproject_text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise ToolchainParityError("Could not parse [project.optional-dependencies].test")

    constraints: dict[str, str] = {}
    for requirement in re.findall(r'"([^\"]+)"', match.group("body")):
        name_match = re.match(r"([A-Za-z0-9_.-]+)(.*)", requirement)
        if not name_match:
            continue
        name = name_match.group(1).lower().replace("_", "-")
        constraints[name] = name_match.group(2)
    return constraints


def main() -> int:
    pyproject_text = _read_text(PYPROJECT)
    canonical_minor = _canonical_python_minor(pyproject_text)
    expected_hook_language = f"python{canonical_minor}"

    precommit_lines = _read_text(PRECOMMIT).splitlines()
    for hook_id in TARGET_HOOKS:
        block = _extract_hook_block(precommit_lines, hook_id)
        found = _hook_language_version(block, hook_id)
        if found != expected_hook_language:
            return _fail(
                f".pre-commit-config.yaml hook '{hook_id}' language_version expected "
                f"'{expected_hook_language}' but found '{found}'."
            )

    action_default_match = re.search(
        r"inputs:\n(?:.|\n)*?python-version:\n(?:.|\n)*?default:\s*['\"]([0-9]+\.[0-9]+)['\"]",
        _read_text(ACTION_SETUP),
    )
    if not action_default_match:
        return _fail("Unable to parse default inputs.python-version from .github/actions/python-test-setup/action.yml")
    if action_default_match.group(1) != canonical_minor:
        return _fail(
            "python-test-setup action default does not match pyproject requires-python lower bound "
            f"('{canonical_minor}')."
        )

    for workflow in sorted(WORKFLOWS_DIR.glob("*.yml")):
        for version in _read_workflow_python_versions(workflow):
            if version != canonical_minor:
                return _fail(
                    f"{workflow.relative_to(ROOT)} uses actions/setup-python with "
                    f"python-version '{version}', expected '{canonical_minor}'."
                )

    constraints = _extract_test_extra_constraints(pyproject_text)
    documented_lines = {
        "- `mypy`: `pyproject.toml` `[project.optional-dependencies].test`",
        "- `ruff`: `pyproject.toml` `[project.optional-dependencies].test`",
        "- `black`: not currently pinned in-repo",
        "- `isort`: not currently pinned in-repo",
    }
    doc_text = _read_text(TOOLCHAIN_DOC)
    missing = [line for line in documented_lines if line not in doc_text]
    if missing:
        return _fail(
            "docs/dev_toolchain_parity.md missing authoritative tool pin documentation lines: "
            + "; ".join(missing)
        )

    for tool in TOOL_PINS:
        if tool in {"mypy", "ruff"} and tool not in constraints:
            return _fail(f"{tool} must be constrained in pyproject.toml test extra.")

    print(
        "Toolchain parity in sync: "
        f"python={canonical_minor}, hook_language={expected_hook_language}, "
        f"workflows_checked={len(list(WORKFLOWS_DIR.glob('*.yml')))}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
