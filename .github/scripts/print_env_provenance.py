#!/usr/bin/env python3
"""Print runtime + tool provenance details for local and CI debugging."""

from __future__ import annotations

import importlib
import platform
import sys
from importlib.metadata import PackageNotFoundError, version

KEY_PACKAGES = (
    "semanticng",
    "pydantic",
    "pytest",
    "pytest-cov",
    "mypy",
    "ruff",
    "pre-commit",
    "gherkin-official",
)


def package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "<not-installed>"


def main() -> int:
    print("=== Python provenance ===")
    print(f"executable: {sys.executable}")
    print(f"version: {sys.version.splitlines()[0]}")
    print(f"implementation: {platform.python_implementation()}")

    print("\n=== Key package versions ===")
    for package in KEY_PACKAGES:
        print(f"{package}: {package_version(package)}")

    semanticng_module = importlib.import_module("semanticng")
    module_path = getattr(semanticng_module, "__file__", "<no __file__>")
    print("\n=== semanticng import target ===")
    print(f"semanticng.__file__: {module_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
