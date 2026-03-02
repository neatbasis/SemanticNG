#!/usr/bin/env python3
"""Fail-fast sentinel for required check name drift.

This guard ensures repository-defined required checks for `main` still exist in
workflow YAML, catching accidental job/workflow renames before branch-protection
configuration silently drifts.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REQUIRED_CONFIG = Path(".github/required-checks-main.json")
WORKFLOWS = [
    Path(".github/workflows/quality-guardrails.yml"),
    Path(".github/workflows/state-renorm-milestone-gate.yml"),
]


def parse_check_contexts(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")

    name_match = re.search(r"^name:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    if not name_match:
        raise ValueError(f"Workflow {path} is missing a top-level name")
    workflow_name = name_match.group(1).strip().strip('"\'')

    jobs_match = re.search(r"^jobs:\n(?P<body>(?:^[ \t].*\n|^\n)*)", text, flags=re.MULTILINE)
    if not jobs_match:
        raise ValueError(f"Workflow {path} is missing a jobs section")

    jobs_body = jobs_match.group("body")
    job_ids = re.findall(r"^\s{2}([A-Za-z0-9_-]+):\s*$", jobs_body, flags=re.MULTILINE)
    return {f"{workflow_name} / {job_id}" for job_id in job_ids}


def main() -> int:
    config = json.loads(REQUIRED_CONFIG.read_text(encoding="utf-8"))
    required_checks = set(config.get("required_checks", []))

    available_checks: set[str] = set()
    for workflow in WORKFLOWS:
        available_checks.update(parse_check_contexts(workflow))

    missing = sorted(required_checks - available_checks)

    print("Required checks configured for main:")
    for check in sorted(required_checks):
        print(f"  - {check}")

    if missing:
        print("\nERROR: required checks missing from workflow definitions:", file=sys.stderr)
        for check in missing:
            print(f"  - {check}", file=sys.stderr)
        print(
            "\nLikely cause: required check job/workflow renamed or removed. "
            "Update workflow names/jobs and branch protection in the same PR.",
            file=sys.stderr,
        )
        return 1

    print("\nSentinel OK: all required checks are present in workflow definitions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
