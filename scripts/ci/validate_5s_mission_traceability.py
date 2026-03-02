#!/usr/bin/env python3
"""Validate 5S mission traceability references stay in sync with canonical sources."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRACEABILITY_PATH = ROOT / "docs" / "5s_mission_traceability.md"
METRICS_PATH = ROOT / "docs" / "process" / "5s_metrics.json"
INVARIANTS_PATH = ROOT / "src" / "state_renormalization" / "invariants.py"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"


def _metric_ids() -> set[str]:
    payload = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    return {
        metric["metric_id"]
        for metric in payload.get("metrics", [])
        if isinstance(metric, dict) and isinstance(metric.get("metric_id"), str)
    }


def _invariant_ids() -> set[str]:
    text = INVARIANTS_PATH.read_text(encoding="utf-8")
    return set(re.findall(r'"([a-z0-9_.-]+\.v\d+)"', text))


def _workflow_names() -> set[str]:
    return {path.stem for path in WORKFLOWS_DIR.glob("*.yml")} | {
        path.stem for path in WORKFLOWS_DIR.glob("*.yaml")
    }


def _traceability_rows() -> list[list[str]]:
    lines = TRACEABILITY_PATH.read_text(encoding="utf-8").splitlines()
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 6:
            continue
        if cells[0] in {"5S principle", "---"} or set(cells[0]) == {"-"}:
            continue
        rows.append(cells)
    return rows


def main() -> int:
    metric_ids = _metric_ids()
    invariant_ids = _invariant_ids()
    workflow_names = _workflow_names()
    rows = _traceability_rows()

    diagnostics: list[str] = []
    expected_principles = {"stability", "signal-health", "staleness", "supply-chain", "specification"}
    found_principles = {row[0] for row in rows}

    if found_principles != expected_principles:
        diagnostics.append(
            "Traceability matrix 5S principles mismatch: "
            f"expected={sorted(expected_principles)} found={sorted(found_principles)}"
        )

    for row in rows:
        principle = row[0]
        governing_cell = row[2]
        enforcing_cell = row[3]
        metric_cell = row[4]

        referenced_metrics = set(re.findall(r"`([^`]+)`", metric_cell))
        for metric in referenced_metrics:
            if metric not in metric_ids:
                diagnostics.append(f"{principle}: unknown metric_id '{metric}'")

        referenced_invariants = set(re.findall(r"`([a-z0-9_.-]+\.v\d+)`", governing_cell))
        for invariant in referenced_invariants:
            if invariant not in invariant_ids:
                diagnostics.append(f"{principle}: unknown invariant_id '{invariant}'")

        referenced_workflows = set(re.findall(r"workflow:`([^`]+)`", enforcing_cell))
        for workflow in referenced_workflows:
            if workflow not in workflow_names:
                diagnostics.append(f"{principle}: unknown workflow name '{workflow}'")

        if not referenced_metrics:
            diagnostics.append(f"{principle}: missing metric_id reference")
        if not referenced_workflows:
            diagnostics.append(f"{principle}: missing workflow reference in 'workflow:`...`' format")

    if diagnostics:
        print("5S mission traceability validation failed:")
        for diagnostic in diagnostics:
            print(f"  - {diagnostic}")
        return 1

    print(
        "5S mission traceability validation passed "
        f"(rows={len(rows)}, metric_ids={len(metric_ids)}, invariant_ids={len(invariant_ids)}, workflows={len(workflow_names)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
