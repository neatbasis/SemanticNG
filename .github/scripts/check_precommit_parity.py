#!/usr/bin/env python3
"""Fail CI when toolchain parity drifts across hook, pyproject, workflow, and docs policy."""

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
REQUIRED_HOOK_LANGUAGE_VERSION = "python3.10"
PARITY_SENSITIVE_WORKFLOWS = (
    ".github/workflows/quality-guardrails.yml",
    ".github/workflows/state-renorm-milestone-gate.yml",
    ".github/workflows/toolchain-parity-weekly.yml",
)
MYPY_SCOPE_DOCS = (
    Path("docs/dev_toolchain_parity.md"),
    Path("docs/DEVELOPMENT.md"),
)


class ParityError(RuntimeError):
    """Raised when expected hook parity constraints are not met."""


def _split_requirement(requirement: str) -> tuple[str, str]:
    parts = re.split(r"([<>=!~].*)", requirement, maxsplit=1)
    name = parts[0].strip().lower().replace("_", "-")
    constraint = parts[1].strip() if len(parts) > 1 else ""
    return name, constraint


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


def _extract_hook_args(hook_block: list[str], hook_id: str) -> list[str]:
    for line in hook_block:
        stripped = line.strip()
        if stripped.startswith("args:"):
            return re.findall(r'"([^"]+)"', stripped)
    raise ParityError(f"Hook '{hook_id}' is missing 'args'.")


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


def _read_requires_python_minor(pyproject_path: Path) -> str:
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    match = re.search(
        r'^requires-python\s*=\s*"\>=([0-9]+\.[0-9]+)"\s*$', pyproject_text, re.MULTILINE
    )
    if not match:
        raise ParityError("Could not parse [project].requires-python as >=X.Y from pyproject.toml.")
    return match.group(1)


def _read_constraint_map_from_pyproject(pyproject_path: Path) -> dict[str, str]:
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    pattern = re.compile(r'^\s*"([^"\s]+)"\s*,?\s*$', flags=re.MULTILINE)

    constraints: dict[str, str] = {}
    for requirement in pattern.findall(pyproject_text):
        name, constraint = _split_requirement(requirement)
        if constraint:
            constraints[name] = constraint
    return constraints


def _extract_toml_array(pyproject_text: str, key: str) -> list[str]:
    match = re.search(rf"^{re.escape(key)}\s*=\s*\[(.*?)\]\s*$", pyproject_text, re.MULTILINE)
    if not match:
        raise ParityError(f"Could not parse '{key}' list from pyproject.toml.")
    return re.findall(r'"([^"]+)"', match.group(1))


def _read_action_default_python_version(action_path: Path) -> str:
    action_text = action_path.read_text(encoding="utf-8")
    match = re.search(
        r"inputs:\n(?:.|\n)*?python-version:\n(?:.|\n)*?default:\s*['\"]([0-9]+\.[0-9]+)['\"]",
        action_text,
    )
    if not match:
        raise ParityError(
            "Could not find default python-version in .github/actions/python-test-setup/action.yml."
        )
    return match.group(1)


def _read_python_versions_from_workflow(workflow_path: Path) -> list[str]:
    text = workflow_path.read_text(encoding="utf-8")
    return re.findall(r"python-version:\s*['\"]?([0-9]+\.[0-9]+)['\"]?", text)


def _as_scope_expr(values: list[str]) -> str:
    return "[" + ", ".join(f'\"{value}\"' for value in values) + "]"


def _ensure_docs_match_mypy_scope(mypy_files: list[str], mypy_hook_args: list[str]) -> None:
    expected_files = f"[tool.mypy].files = {_as_scope_expr(mypy_files)}"
    expected_args = f"args: {_as_scope_expr(mypy_hook_args)}"

    for doc in MYPY_SCOPE_DOCS:
        text = doc.read_text(encoding="utf-8")
        missing: list[str] = []
        if expected_files not in text:
            missing.append(expected_files)
        if expected_args not in text:
            missing.append(expected_args)
        if missing:
            print("Pre-commit parity failure: documented mypy scope drift.")
            print(f"  file: {doc}")
            print("  missing exact string(s):")
            for entry in missing:
                print(f"    - {entry}")
            raise ParityError("Documented mypy scope strings are out of sync.")


def main() -> int:
    config_lines = Path(".pre-commit-config.yaml").read_text(encoding="utf-8").splitlines()
    pyproject_path = Path("pyproject.toml")
    pyproject_text = pyproject_path.read_text(encoding="utf-8")

    tier1 = _extract_toml_array(pyproject_text, "tier1_strict")
    tier2 = _extract_toml_array(pyproject_text, "tier2_extended")
    if tier2 != ["src", "tests"]:
        print("Pre-commit parity failure: unexpected Tier 2 canonical scope.")
        print("  expected: ['src', 'tests']")
        print(f"  found: {tier2}")
        return 1

    mypy_files = _extract_toml_array(pyproject_text, "files")
    if mypy_files != tier1:
        print("Pre-commit parity failure: [tool.mypy].files must match tier1_strict.")
        print(f"  tier1_strict: {tier1}")
        print(f"  [tool.mypy].files: {mypy_files}")
        return 1

    mypy_block = _extract_hook_block(config_lines, "mypy")
    mypy_hook_args = _extract_hook_args(mypy_block, "mypy")
    expected_mypy_hook_args = ["--config-file=pyproject.toml", *tier1]
    if mypy_hook_args != expected_mypy_hook_args:
        print("Pre-commit parity failure: mypy hook args must match tier1_strict scope.")
        print(f"  expected: {expected_mypy_hook_args}")
        print(f"  found: {mypy_hook_args}")
        return 1

    _ensure_docs_match_mypy_scope(mypy_files, expected_mypy_hook_args)

    mypy_dep_specs = _extract_additional_dependencies(mypy_block)
    mypy_constraints = {
        _split_requirement(dep)[0]: _split_requirement(dep)[1] for dep in mypy_dep_specs
    }

    missing = [pkg for pkg in REQUIRED_MYPY_PACKAGES if pkg not in mypy_constraints]
    if missing:
        print("Pre-commit parity failure: missing mypy additional_dependencies.")
        print("  expected packages:")
        for package in REQUIRED_MYPY_PACKAGES:
            print(f"    - {package}")
        print("  missing packages:")
        for package in missing:
            print(f"    - {package}")
        return 1

    constraints = _read_constraint_map_from_pyproject(pyproject_path)
    for package in REQUIRED_MYPY_PACKAGES:
        expected_constraint = constraints.get(package)
        hook_constraint = mypy_constraints[package]
        if expected_constraint is None:
            print("Pre-commit parity failure: required package constraint missing from pyproject.")
            print(f"  package: {package}")
            return 1
        if hook_constraint != expected_constraint:
            print("Pre-commit parity failure: dependency constraint mismatch.")
            print(f"  package: {package}")
            print(f"  expected constraint from pyproject: {expected_constraint}")
            print(f"  found in pre-commit: {hook_constraint}")
            return 1

    py_minor = _read_requires_python_minor(pyproject_path)
    expected_hook_language_version = f"python{py_minor}"

    for hook_id in ("mypy", "ruff", "ruff-format"):
        hook_block = _extract_hook_block(config_lines, hook_id)
        language_version = _extract_hook_language_version(hook_block, hook_id)
        if (
            language_version != expected_hook_language_version
            or language_version != REQUIRED_HOOK_LANGUAGE_VERSION
        ):
            print("Pre-commit parity failure: language_version mismatch.")
            print(f"  hook: {hook_id}")
            print(f"  expected: {expected_hook_language_version}")
            print(f"  found: {language_version}")
            return 1

    action_version = _read_action_default_python_version(
        Path(".github/actions/python-test-setup/action.yml")
    )
    if action_version != py_minor:
        print("Pre-commit parity failure: python-test-setup action default is out of sync.")
        print(f"  expected: {py_minor}")
        print(f"  found: {action_version}")
        return 1

    for workflow in PARITY_SENSITIVE_WORKFLOWS:
        versions = _read_python_versions_from_workflow(Path(workflow))
        mismatched = [v for v in versions if v != py_minor]
        if mismatched:
            print("Pre-commit parity failure: workflow python-version mismatch.")
            print(f"  workflow: {workflow}")
            print(f"  expected: {py_minor}")
            print(f"  found: {', '.join(versions)}")
            return 1

    print(
        "Pre-commit parity in sync: "
        f"tier1={tier1}; "
        f"tier2={tier2}; "
        f"mypy deps={', '.join(REQUIRED_MYPY_PACKAGES)}; "
        f"language_version={expected_hook_language_version}; "
        f"python_baseline={py_minor}; "
        f"workflows_checked={', '.join(PARITY_SENSITIVE_WORKFLOWS)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
