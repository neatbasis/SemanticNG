#!/usr/bin/env python3
"""Validate sprint handoff artifacts for sprint-close/governance pull requests."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF_DIR = ROOT / "docs" / "sprint_handoffs"
HANDOFF_PATTERN = "sprint-*-handoff.md"
REQUIRED_HEADINGS = (
    "## Exit criteria pass/fail matrix",
    "## Open risk register with owners/dates",
    "## Next-sprint preload mapped to capability IDs",
)

GOVERNANCE_INPUTS = {
    "docs/dod_manifest.json",
    "docs/no_regression_budget.json",
    "docs/sprint_handoffs/",
}
SPRINT_CLOSE_MARKERS = {"sprint-close", "sprint_close", "sprint close"}


def _changed_files(base_sha: str, head_sha: str) -> list[str]:
    output = subprocess.check_output(["git", "diff", "--name-only", base_sha, head_sha], text=True)
    return [line.strip() for line in output.splitlines() if line.strip()]


def _load_event_payload() -> dict:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return {}
    payload_path = Path(event_path)
    if not payload_path.exists():
        return {}
    return json.loads(payload_path.read_text(encoding="utf-8"))


def _is_sprint_close_or_governance_pr(changed_files: Iterable[str], payload: dict) -> bool:
    changed = set(changed_files)
    if any(path in changed for path in GOVERNANCE_INPUTS if not path.endswith("/")):
        return True
    if any(path.startswith("docs/sprint_handoffs/") for path in changed):
        return True

    pull_request = payload.get("pull_request") if isinstance(payload, dict) else None
    if not isinstance(pull_request, dict):
        return False

    title = str(pull_request.get("title", "")).lower()
    body = str(pull_request.get("body", "")).lower()
    if any(marker in title or marker in body for marker in SPRINT_CLOSE_MARKERS):
        return True

    labels = pull_request.get("labels", [])
    label_names = {
        str(label.get("name", "")).lower() for label in labels if isinstance(label, dict)
    }
    return any(marker in label_names for marker in SPRINT_CLOSE_MARKERS | {"governance"})


def _section_body(markdown_text: str, heading: str) -> str | None:
    lines = markdown_text.splitlines()
    for idx, line in enumerate(lines):
        if line.strip() != heading:
            continue
        body_lines: list[str] = []
        for inner in lines[idx + 1 :]:
            stripped = inner.strip()
            if stripped.startswith("## ") and stripped != heading:
                break
            body_lines.append(inner)
        return "\n".join(body_lines)
    return None


def _extract_markdown_table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    return rows


def _normalize_capability_id(raw: str) -> str:
    return raw.strip().strip("`")


def _validate_handoff_file(path: Path, capability_ids: set[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    mismatches: list[str] = []

    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            mismatches.append(f"{path}: missing heading '{heading}'.")

    matrix = _section_body(text, REQUIRED_HEADINGS[0])
    if matrix is None or "| Exit criterion |" not in matrix or "| Status" not in matrix:
        mismatches.append(f"{path}: exit-criteria section must include a status matrix table.")

    risks = _section_body(text, REQUIRED_HEADINGS[1])
    if risks is None:
        mismatches.append(f"{path}: missing open risk register section.")
    else:
        risk_rows = _extract_markdown_table_rows(risks)
        if len(risk_rows) < 2:
            mismatches.append(
                f"{path}: risk register must include header and at least one risk row."
            )
        else:
            for idx, row in enumerate(risk_rows[1:], start=1):
                if len(row) < 3:
                    mismatches.append(
                        f"{path}: risk row {idx} must include owner and target date columns."
                    )
                    continue
                owner = row[1].strip()
                target_date = row[2].strip()
                if not owner:
                    mismatches.append(f"{path}: risk row {idx} owner cannot be empty.")
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", target_date):
                    mismatches.append(f"{path}: risk row {idx} target date must be YYYY-MM-DD.")

    preload = _section_body(text, REQUIRED_HEADINGS[2])
    if preload is None:
        mismatches.append(f"{path}: missing next-sprint preload section.")
    else:
        preload_rows = _extract_markdown_table_rows(preload)
        if len(preload_rows) < 2:
            mismatches.append(
                f"{path}: preload section must include header and at least one capability row."
            )
        else:
            for idx, row in enumerate(preload_rows[1:], start=1):
                capability_id = _normalize_capability_id(row[0]) if row else ""
                if not capability_id:
                    mismatches.append(f"{path}: preload row {idx} capability id cannot be empty.")
                    continue
                if capability_id not in capability_ids:
                    mismatches.append(
                        f"{path}: preload row {idx} capability id '{capability_id}' not found in docs/dod_manifest.json."
                    )

    return mismatches


def _load_capability_ids() -> set[str]:
    manifest = json.loads((ROOT / "docs" / "dod_manifest.json").read_text(encoding="utf-8"))
    return {
        str(cap.get("id"))
        for cap in manifest.get("capabilities", [])
        if isinstance(cap, dict) and isinstance(cap.get("id"), str)
    }


def main() -> int:
    head_sha = (
        os.environ.get("HEAD_SHA")
        or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    )
    base_sha = (
        os.environ.get("BASE_SHA")
        or subprocess.check_output(["git", "rev-parse", f"{head_sha}~1"], text=True).strip()
    )

    changed_files = _changed_files(base_sha, head_sha)
    payload = _load_event_payload()

    if not _is_sprint_close_or_governance_pr(changed_files, payload):
        print("Not a sprint-close/governance PR; skipping sprint handoff validation.")
        return 0

    if not HANDOFF_DIR.exists():
        print("Missing required canonical sprint handoff location: docs/sprint_handoffs/.")
        return 1

    handoff_files = sorted(path for path in HANDOFF_DIR.glob(HANDOFF_PATTERN) if path.is_file())
    if not handoff_files:
        print(
            "At least one sprint handoff artifact is required at docs/sprint_handoffs/sprint-<n>-handoff.md."
        )
        return 1

    capability_ids = _load_capability_ids()
    mismatches: list[str] = []
    for handoff in handoff_files:
        mismatches.extend(_validate_handoff_file(handoff, capability_ids))

    if mismatches:
        print("Sprint handoff validation failed:")
        for mismatch in mismatches:
            print(f"  - {mismatch}")
        return 1

    print("Sprint handoff validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
