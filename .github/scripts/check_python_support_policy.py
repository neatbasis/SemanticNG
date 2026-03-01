#!/usr/bin/env python3
"""Fail CI when Python version policy drifts across pyproject, README, and CI setup."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def read_requires_python(pyproject_path: Path) -> str:
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    match = re.search(
        r"^requires-python\s*=\s*\"([^\"]+)\"\s*$", pyproject_text, flags=re.MULTILINE
    )
    if not match:
        raise ValueError("Could not find [project].requires-python in pyproject.toml.")
    return match.group(1)


def expected_readme_requirement(requires_python: str) -> str:
    match = re.fullmatch(r">=([0-9]+\.[0-9]+)", requires_python.strip())
    if not match:
        raise ValueError(
            "Unsupported [project].requires-python format; expected a simple '>=X.Y' constraint."
        )
    return f"- Python **{match.group(1)}+**"


def read_ci_default_python_version(action_path: Path) -> str:
    action_text = action_path.read_text(encoding="utf-8")
    match = re.search(
        r"inputs:\n(?:.|\n)*?python-version:\n(?:.|\n)*?default:\s*['\"]([0-9]+\.[0-9]+)['\"]",
        action_text,
    )
    if not match:
        raise ValueError(
            "Could not find a default Python version in .github/actions/python-test-setup/action.yml."
        )
    return match.group(1)


def main() -> int:
    requires_python = read_requires_python(Path("pyproject.toml"))
    expected_line = expected_readme_requirement(requires_python)
    expected_ci_version = expected_line.removeprefix("- Python **").removesuffix("+**")

    readme_lines = Path("README.md").read_text(encoding="utf-8").splitlines()
    python_requirement_lines = [
        line.strip() for line in readme_lines if line.strip().startswith("- Python **")
    ]

    if python_requirement_lines != [expected_line]:
        print("README Python requirement is out of sync with pyproject policy.")
        print(f"  pyproject.toml requires-python: {requires_python}")
        print(f"  expected README line: {expected_line}")
        if python_requirement_lines:
            print("  found README line(s):")
            for line in python_requirement_lines:
                print(f"    - {line}")
        else:
            print("  found README line(s): <none>")
        return 1

    ci_default_python = read_ci_default_python_version(
        Path(".github/actions/python-test-setup/action.yml")
    )
    if ci_default_python != expected_ci_version:
        print("CI default Python version is out of sync with pyproject policy.")
        print(f"  pyproject.toml requires-python: {requires_python}")
        print(f"  expected CI default python-version: {expected_ci_version}")
        print(f"  found CI default python-version: {ci_default_python}")
        return 1

    print(
        "Python support policy in sync: "
        f"requires-python={requires_python}, readme={expected_line}, ci_default={ci_default_python}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
