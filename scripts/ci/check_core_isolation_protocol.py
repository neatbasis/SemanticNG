#!/usr/bin/env python3
"""Detect obvious protocol breaches in src/core diffs."""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_INIT = ROOT / "src" / "core" / "__init__.py"

FORBIDDEN_IMPORT_PREFIXES = (
    "state_renormalization",
    "features",
    "src.features",
)
ORCHESTRATION_MARKERS = (
    "orchestr",
    "workflow",
    "pipeline",
    "feature flag",
    "scenario",
    "step",
)


@dataclass(frozen=True)
class Violation:
    code: str
    file_path: str
    line_number: int | None
    message: str
    remediation: str


def _git_output(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=ROOT, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git command failed")
    return proc.stdout


def _core_diff() -> str:
    return _git_output(["diff", "--cached", "--unified=0", "--", "src/core"])


def _changed_core_paths() -> tuple[str, ...]:
    out = _git_output(["diff", "--cached", "--name-only", "--diff-filter=ACMR", "--", "src/core"])
    return tuple(line.strip() for line in out.splitlines() if line.strip())


def _parse_added_lines(diff_text: str) -> list[tuple[str, int | None, str]]:
    file_path = ""
    next_line_number: int | None = None
    added: list[tuple[str, int | None, str]] = []

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ b/"):
            file_path = raw_line[6:]
            next_line_number = None
            continue

        if raw_line.startswith("@@"):
            match = re.search(r"\+(\d+)", raw_line)
            next_line_number = int(match.group(1)) if match else None
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            added.append((file_path, next_line_number, raw_line[1:]))
            if next_line_number is not None:
                next_line_number += 1
            continue

        if raw_line.startswith("-") and not raw_line.startswith("---"):
            continue

        if next_line_number is not None and not raw_line.startswith("\\"):
            next_line_number += 1

    return added


def _detect_forbidden_imports(added_lines: list[tuple[str, int | None, str]]) -> list[Violation]:
    violations: list[Violation] = []
    import_re = re.compile(r"^\s*(?:from|import)\s+([A-Za-z0-9_\.]+)")
    for file_path, line_number, line in added_lines:
        if not file_path.endswith(".py"):
            continue
        match = import_re.match(line)
        if not match:
            continue
        imported = match.group(1)
        if imported.startswith(FORBIDDEN_IMPORT_PREFIXES):
            violations.append(
                Violation(
                    code="CIP-FORBIDDEN-IMPORT",
                    file_path=file_path,
                    line_number=line_number,
                    message=f"forbidden import in core boundary: '{imported}'",
                    remediation=(
                        "Keep src/core isolated from orchestration/application namespaces; "
                        "move this import behind adapters outside src/core."
                    ),
                )
            )
    return violations


def _detect_orchestration_markers(added_lines: list[tuple[str, int | None, str]]) -> list[Violation]:
    violations: list[Violation] = []
    for file_path, line_number, line in added_lines:
        if not file_path.endswith((".py", ".md")):
            continue
        lowered = line.lower()
        for marker in ORCHESTRATION_MARKERS:
            if marker in lowered:
                violations.append(
                    Violation(
                        code="CIP-ORCHESTRATION-LEAK",
                        file_path=file_path,
                        line_number=line_number,
                        message=f"orchestration leakage marker '{marker}' found in added line",
                        remediation=(
                            "Preserve I3: src/core must stay foundational only; "
                            "document orchestration semantics outside src/core."
                        ),
                    )
                )
                break
    return violations


def _detect_extra_exports(changed_core_paths: tuple[str, ...]) -> list[Violation]:
    if "src/core/__init__.py" not in changed_core_paths:
        return []
    module = ast.parse(CORE_INIT.read_text(encoding="utf-8"))

    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
            try:
                exports = ast.literal_eval(node.value)
            except Exception:
                return [
                    Violation(
                        code="CIP-EXPORT-SURFACE-OPAQUE",
                        file_path="src/core/__init__.py",
                        line_number=getattr(node, "lineno", None),
                        message="__all__ must be a literal sequence so API surface can be audited",
                        remediation="Set __all__ exactly to ['__version__'].",
                    )
                ]
            if tuple(exports) != ("__version__",):
                return [
                    Violation(
                        code="CIP-EXTRA-EXPORT",
                        file_path="src/core/__init__.py",
                        line_number=getattr(node, "lineno", None),
                        message=f"core exports must remain ['__version__']; found {list(exports)}",
                        remediation="Remove extra exports and keep only __version__ in src/core/__init__.py.",
                    )
                ]
            return []

    return [
        Violation(
            code="CIP-MISSING-ALL",
            file_path="src/core/__init__.py",
            line_number=None,
            message="missing __all__ declaration in src/core/__init__.py",
            remediation="Declare __all__ = ['__version__'] to preserve I1 surface minimality.",
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    changed_core_paths = _changed_core_paths()
    if not changed_core_paths:
        print("No staged src/core changes detected; core isolation protocol check skipped.")
        return 0

    diff_text = _core_diff()
    added_lines = _parse_added_lines(diff_text)

    violations: list[Violation] = []
    violations.extend(_detect_extra_exports(changed_core_paths))
    violations.extend(_detect_forbidden_imports(added_lines))
    violations.extend(_detect_orchestration_markers(added_lines))

    if not violations:
        print("Core isolation protocol checks passed for staged src/core changes.")
        return 0

    print("Core isolation protocol violations detected:")
    for violation in violations:
        location = violation.file_path
        if violation.line_number is not None:
            location = f"{location}:{violation.line_number}"
        print(f"- [{violation.code}] {location} -> {violation.message}")
        print(f"  Remediation: {violation.remediation}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
