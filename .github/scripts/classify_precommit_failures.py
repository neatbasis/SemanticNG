#!/usr/bin/env python3
"""Classify pre-commit failures and emit a concise Markdown summary."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

AUTO_FIX_PATTERN = re.compile(r"files were modified by this hook", re.IGNORECASE)
IMPORT_NOT_FOUND_PATTERN = re.compile(r"\bimport-not-found\b")
RUFF_CODE_PATTERN = re.compile(r"\b([A-Z]{1,4}\d{2,4})\b")
MYPY_ERROR_PATTERN = re.compile(r"error: .*?\[(?P<code>[^\]]+)\]")


def classify(log_text: str) -> tuple[bool, bool, list[str], list[str]]:
    auto_fix_required = bool(AUTO_FIX_PATTERN.search(log_text))
    missing_dependency = bool(IMPORT_NOT_FOUND_PATTERN.search(log_text))

    ruff_codes: set[str] = set()
    mypy_codes: set[str] = set()

    for match in RUFF_CODE_PATTERN.finditer(log_text):
        code = match.group(1)
        if code in {"INFO", "WARN", "ERROR", "FAIL"}:
            continue
        if code.startswith(("E", "W", "F", "I", "N", "UP", "PL", "RUF", "B", "C", "S", "D")):
            ruff_codes.add(code)

    for match in MYPY_ERROR_PATTERN.finditer(log_text):
        mypy_codes.add(match.group("code"))

    return auto_fix_required, missing_dependency, sorted(ruff_codes), sorted(mypy_codes)


def render_summary(
    auto_fix_required: bool,
    missing_dependency: bool,
    ruff_codes: list[str],
    mypy_codes: list[str],
) -> str:
    lines = ["## Pre-commit failure classification", ""]

    if not any([auto_fix_required, missing_dependency, ruff_codes, mypy_codes]):
        lines.append("- ✅ No known failure signatures detected in `precommit.log`.")
        return "\n".join(lines)

    if auto_fix_required:
        lines.append(
            "- **Auto-fix required** (`files were modified`): run `pre-commit run --all-files`, review changes, and commit the updated files."
        )

    if missing_dependency:
        lines.append(
            "- **Missing import/dependency** (`import-not-found`): install sync deps (`pip install -r requirements.txt`) and verify import paths/module names."
        )

    if ruff_codes or mypy_codes:
        detail_parts: list[str] = []
        if ruff_codes:
            detail_parts.append(f"Ruff codes: `{', '.join(ruff_codes[:10])}`")
        if mypy_codes:
            detail_parts.append(f"mypy strict codes: `{', '.join(mypy_codes[:10])}`")
        details = "; ".join(detail_parts)
        lines.append(
            "- **Rule violations**: "
            f"{details}. Remediate by fixing lint/type issues locally with `pre-commit run --all-files -v` and `mypy --config-file=pyproject.toml src tests`."
        )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default="precommit.log", help="Path to pre-commit verbose log")
    args = parser.parse_args()

    path = Path(args.log)
    if not path.exists():
        print(
            "## Pre-commit failure classification\n\n- ⚠️ `precommit.log` not found; classification skipped."
        )
        return 0

    log_text = path.read_text(encoding="utf-8", errors="replace")
    result = classify(log_text)
    print(render_summary(*result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
