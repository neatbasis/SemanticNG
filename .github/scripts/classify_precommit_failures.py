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
HOOK_BLOCK_PATTERN = re.compile(
    r"^(?P<name>.+?)\.{10,}(?P<status>Passed|Failed)\s*$", re.MULTILINE
)
FILES_LIST_PATTERN = re.compile(r"^files?:\s*(?P<files>.+)$", re.MULTILINE)

TAXONOMY_KEYS: tuple[str, ...] = ("ruff", "mypy", "pytest", "autofix_drift", "infra_setup")
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
    if auto_fix_required:
        classes.add("autofix_drift")
    if missing_dependency:
        classes.add("infra_setup")

    failing_hooks = extract_failing_hooks(log_text)

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
        "failing_hooks": failing_hooks,
        "touched_paths": sorted(touched_paths),
    }



def extract_failing_hooks(log_text: str) -> list[dict[str, Any]]:
    hooks: list[dict[str, Any]] = []
    blocks = list(HOOK_BLOCK_PATTERN.finditer(log_text))
    for index, block in enumerate(blocks):
        if block.group("status") != "Failed":
            continue
        start = block.end()
        end = blocks[index + 1].start() if index + 1 < len(blocks) else len(log_text)
        section = log_text[start:end]

        files: set[str] = set(PATH_PATTERN.findall(section))
        files_line = FILES_LIST_PATTERN.search(section)
        if files_line:
            for candidate in files_line.group("files").split(","):
                file_text = candidate.strip().strip('"').strip("'")
                if file_text:
                    files.add(file_text)

        hooks.append({"name": block.group("name").strip(), "files": sorted(files)})
    return hooks


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
            "- **Auto-fix drift** (`files were modified`): run `pre-commit run --all-files`, review changes, and commit updates."
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

    failing_hooks = classification.get("failing_hooks", [])
    if failing_hooks:
        lines.append("- **Failing hooks:**")
        for hook in failing_hooks[:10]:
            first_files = hook.get("files", [])[:5]
            file_segment = f" (files: `{', '.join(first_files)}`)" if first_files else ""
            lines.append(f"  - `{hook.get('name', 'unknown hook')}`{file_segment}")

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
