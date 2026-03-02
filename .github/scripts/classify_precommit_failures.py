#!/usr/bin/env python3
"""Classify pre-commit failures and emit machine-readable artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

AUTO_FIX_PATTERN = re.compile(r"files were modified by this hook", re.IGNORECASE)
IMPORT_NOT_FOUND_PATTERN = re.compile(r"\bimport-not-found\b")
RUFF_CODE_PATTERN = re.compile(r"\b([A-Z]{1,4}\d{2,4})\b")
MYPY_ERROR_PATTERN = re.compile(r"error: .*?\[(?P<code>[^\]]+)\]")
PYTEST_ERROR_PATTERN = re.compile(
    r"(=+\s+FAILURES\s+=+|\bE\s+AssertionError\b|\bFAILED\s+tests?/)",
    re.IGNORECASE,
)
PATH_PATTERN = re.compile(r"\b(?P<path>(?:src|tests|docs|\.github)/[\w./-]+\.[A-Za-z0-9]+)")

TAXONOMY_KEYS: tuple[str, ...] = ("ruff", "mypy", "pytest", "infra_setup")
SCHEMA_VERSION = "1.0"


def classify(log_text: str) -> dict[str, Any]:
    classes: set[str] = set()
    ruff_codes: set[str] = set()
    mypy_codes: set[str] = set()
    touched_paths: set[str] = set(PATH_PATTERN.findall(log_text))

    auto_fix_required = bool(AUTO_FIX_PATTERN.search(log_text))
    missing_dependency = bool(IMPORT_NOT_FOUND_PATTERN.search(log_text))

    for match in RUFF_CODE_PATTERN.finditer(log_text):
        code = match.group(1)
        if code in {"INFO", "WARN", "ERROR", "FAIL"}:
            continue
        if code.startswith(("E", "W", "F", "I", "N", "UP", "PL", "RUF", "B", "C", "S", "D")):
            ruff_codes.add(code)

    for match in MYPY_ERROR_PATTERN.finditer(log_text):
        mypy_codes.add(match.group("code"))

    if ruff_codes:
        classes.add("ruff")
    if mypy_codes:
        classes.add("mypy")
    if PYTEST_ERROR_PATTERN.search(log_text):
        classes.add("pytest")
    if auto_fix_required or missing_dependency:
        classes.add("infra_setup")

    return {
        "schema_version": SCHEMA_VERSION,
        "taxonomy": list(TAXONOMY_KEYS),
        "classes_detected": sorted(classes),
        "signals": {
            "auto_fix_required": auto_fix_required,
            "missing_dependency": missing_dependency,
            "ruff_codes": sorted(ruff_codes),
            "mypy_codes": sorted(mypy_codes),
            "pytest_failure_detected": bool(PYTEST_ERROR_PATTERN.search(log_text)),
        },
        "touched_paths": sorted(touched_paths),
    }


def render_summary(classification: dict[str, Any]) -> str:
    lines = ["## Pre-commit failure classification", ""]

    detected = classification["classes_detected"]
    signals = classification["signals"]

    if not detected:
        lines.append("- ✅ No known failure signatures detected in `precommit.log`.")
        return "\n".join(lines)

    lines.append(f"- **Detected classes:** `{', '.join(detected)}`")

    if signals["auto_fix_required"]:
        lines.append(
            "- **Auto-fix required** (`files were modified`): run `pre-commit run --all-files`, review changes, and commit updates."
        )

    if signals["missing_dependency"]:
        lines.append(
            "- **Missing dependency/import** (`import-not-found`): sync dependencies and verify import/module paths."
        )

    if signals["ruff_codes"]:
        lines.append(f"- **Ruff codes:** `{', '.join(signals['ruff_codes'][:10])}`")

    if signals["mypy_codes"]:
        lines.append(f"- **mypy codes:** `{', '.join(signals['mypy_codes'][:10])}`")

    if signals["pytest_failure_detected"]:
        lines.append("- **Pytest signal detected** in hook output.")

    touched = classification["touched_paths"]
    lines.append(
        "- **Touched paths (observed in log):** "
        + (f"`{', '.join(touched[:20])}`" if touched else "none detected")
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default="precommit.log", help="Path to pre-commit verbose log")
    parser.add_argument(
        "--json-out",
        default="precommit_failure_classification.json",
        help="Path to JSON classification output",
    )
    parser.add_argument(
        "--md-out",
        default="precommit_failure_classification.md",
        help="Path to Markdown summary output",
    )
    args = parser.parse_args()

    path = Path(args.log)
    if not path.exists():
        summary = (
            "## Pre-commit failure classification\n\n"
            "- ⚠️ `precommit.log` not found; classification skipped."
        )
        Path(args.md_out).write_text(summary + "\n", encoding="utf-8")
        Path(args.json_out).write_text(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "taxonomy": list(TAXONOMY_KEYS),
                    "classes_detected": [],
                    "signals": {},
                    "touched_paths": [],
                    "error": "log_not_found",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(summary)
        return 0

    log_text = path.read_text(encoding="utf-8", errors="replace")
    classification = classify(log_text)
    summary = render_summary(classification)

    Path(args.json_out).write_text(json.dumps(classification, indent=2) + "\n", encoding="utf-8")
    Path(args.md_out).write_text(summary + "\n", encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
