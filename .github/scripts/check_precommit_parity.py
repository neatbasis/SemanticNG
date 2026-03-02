#!/usr/bin/env python3
"""Fail CI when toolchain parity drifts across hook, pyproject, workflow, and docs policy."""

from __future__ import annotations

import re
import sys
import json
from pathlib import Path

POLICY_PATH = Path("docs/toolchain_parity_policy.json")
REQUIRED_MYPY_PACKAGES = (
    "pydantic",
    "pytest",
    "gherkin-official",
    "typing-extensions",
)


class ParityError(RuntimeError):
    """Raised when expected hook parity constraints are not met."""


def _load_policy() -> dict[str, object]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _report_drift(file_path: Path | str, key: str, expected: object, found: object) -> None:
    print("Pre-commit parity failure: drift detected.")
    print(f"  file: {file_path}")
    print(f"  key: {key}")
    print(f"  expected: {expected}")
    print(f"  found: {found}")


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


def _ensure_docs_match_mypy_scope(
    mypy_files: list[str], mypy_hook_args: list[str], parity_docs: list[Path]
) -> None:
    expected_files = f"- Tier 1 mypy scope: `{mypy_files}`"
    expected_args = f"- Tier 1 mypy hook args: `{mypy_hook_args}`"

    for doc in parity_docs:
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


def _ensure_command_parity_strings(canonical_make_targets: list[str], parity_docs: list[Path]) -> None:
    workflow = Path(".github/workflows/quality-guardrails.yml")
    workflow_text = workflow.read_text(encoding="utf-8")

    missing_workflow = [target for target in canonical_make_targets if target not in workflow_text]
    if missing_workflow:
        print("Pre-commit parity failure: workflow command parity drift.")
        print(f"  workflow: {workflow}")
        print("  missing exact string(s):")
        for entry in missing_workflow:
            print(f"    - {entry}")
        raise ParityError("Workflow command parity strings are out of sync.")

    for doc in parity_docs:
        text = doc.read_text(encoding="utf-8")
        missing_doc = [target for target in canonical_make_targets if target not in text]
        if missing_doc:
            print("Pre-commit parity failure: docs command parity drift.")
            print(f"  file: {doc}")
            print("  missing exact string(s):")
            for entry in missing_doc:
                print(f"    - {entry}")
            raise ParityError("Documentation command parity strings are out of sync.")


def main() -> int:
    config_lines = Path(".pre-commit-config.yaml").read_text(encoding="utf-8").splitlines()
    pyproject_path = Path("pyproject.toml")
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    policy = _load_policy()

    python_version = str(policy["python_version"])
    required_hook_language_version = str(policy["hook_language_version"])
    policy_tier1 = list(policy["mypy"]["tier1_scope"])
    policy_tier2 = list(policy["mypy"]["tier2_scope"])
    canonical_make_targets = list(policy["canonical_make_targets"])
    parity_workflows = list(policy["parity_sensitive_workflows"])
    parity_docs = [Path(path) for path in list(policy["parity_docs"])]

    tier1 = _extract_toml_array(pyproject_text, "tier1_strict")
    tier2 = _extract_toml_array(pyproject_text, "tier2_extended")
    if tier2 != policy_tier2:
        _report_drift("pyproject.toml", "tool.semanticng.mypy_tiers.tier2_extended", policy_tier2, tier2)
        return 1

    mypy_files = _extract_toml_array(pyproject_text, "files")
    if mypy_files != tier1:
        _report_drift("pyproject.toml", "tool.mypy.files", tier1, mypy_files)
        return 1

    if tier1 != policy_tier1:
        _report_drift("pyproject.toml", "tool.semanticng.mypy_tiers.tier1_strict", policy_tier1, tier1)
        return 1

    mypy_block = _extract_hook_block(config_lines, "mypy")
    mypy_hook_args = _extract_hook_args(mypy_block, "mypy")
    expected_mypy_hook_args = ["--config-file=pyproject.toml", *tier1]
    if mypy_hook_args != expected_mypy_hook_args:
        _report_drift(".pre-commit-config.yaml", "hooks.mypy.args", expected_mypy_hook_args, mypy_hook_args)
        return 1

    _ensure_docs_match_mypy_scope(mypy_files, expected_mypy_hook_args, parity_docs)
    _ensure_command_parity_strings(canonical_make_targets, parity_docs)

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
            _report_drift("pyproject.toml", f"project.optional-dependencies.test[{package}]", "<constraint>", None)
            return 1
        if hook_constraint != expected_constraint:
            _report_drift(
                ".pre-commit-config.yaml",
                f"hooks.mypy.additional_dependencies[{package}]",
                expected_constraint,
                hook_constraint,
            )
            return 1

    py_minor = _read_requires_python_minor(pyproject_path)
    expected_hook_language_version = f"python{py_minor}"
    if py_minor != python_version:
        _report_drift("pyproject.toml", "project.requires-python", python_version, py_minor)
        return 1

    for hook_id in ("mypy", "ruff", "ruff-format"):
        hook_block = _extract_hook_block(config_lines, hook_id)
        language_version = _extract_hook_language_version(hook_block, hook_id)
        if (
            language_version != expected_hook_language_version
            or language_version != required_hook_language_version
        ):
            _report_drift(
                ".pre-commit-config.yaml",
                f"hooks.{hook_id}.language_version",
                expected_hook_language_version,
                language_version,
            )
            return 1

    action_version = _read_action_default_python_version(
        Path(".github/actions/python-test-setup/action.yml")
    )
    if action_version != py_minor:
        _report_drift(
            ".github/actions/python-test-setup/action.yml",
            "inputs.python-version.default",
            py_minor,
            action_version,
        )
        return 1

    for workflow in parity_workflows:
        versions = _read_python_versions_from_workflow(Path(workflow))
        mismatched = [v for v in versions if v != py_minor]
        if mismatched:
            _report_drift(workflow, "python-version", py_minor, versions)
            return 1

    print(
        "Pre-commit parity in sync: "
        f"tier1={tier1}; "
        f"tier2={tier2}; "
        f"mypy deps={', '.join(REQUIRED_MYPY_PACKAGES)}; "
        f"language_version={expected_hook_language_version}; "
        f"python_baseline={py_minor}; "
        f"workflows_checked={', '.join(parity_workflows)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
