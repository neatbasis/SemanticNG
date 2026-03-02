#!/usr/bin/env python3
"""Refresh script-analytics sprint handoff status table from generated artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HANDOFF = ROOT / "docs" / "sprint_handoffs" / "script-analytics-5-sprint-plan.md"
DEFAULT_INVENTORY = ROOT / "docs" / "process" / "script_entrypoints_inventory.json"
DEFAULT_UNUSED_SUMMARY = ROOT / "artifacts" / "unused_code" / "summary.json"
DEFAULT_PARITY_OUTPUT = ROOT / "artifacts" / "script_docs_parity" / "validator_output.json"
START_MARKER = "<!-- script-analytics-status-table:start -->"
END_MARKER = "<!-- script-analytics-status-table:end -->"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--unused-summary", type=Path, default=DEFAULT_UNUSED_SUMMARY)
    parser.add_argument("--docs-parity-output", type=Path, default=DEFAULT_PARITY_OUTPUT)
    return parser.parse_args()


def _coverage_percent(inventory_payload: list[dict[str, object]]) -> float:
    if not inventory_payload:
        return 0.0
    documented_count = sum(1 for row in inventory_payload if row.get("documented") is True)
    return round((documented_count / len(inventory_payload)) * 100.0, 2)


def _undocumented_count(inventory_payload: list[dict[str, object]]) -> int:
    return sum(1 for row in inventory_payload if row.get("documented") is not True)


def _diagnostics_trend(unused_payload: dict[str, object]) -> str:
    surfaces = unused_payload.get("surfaces", [])
    if not isinstance(surfaces, list):
        return "unknown"
    total = 0
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        count = surface.get("diagnostic_count")
        if isinstance(count, int):
            total += count
    if total == 0:
        return "flat (0 diagnostics)"
    return f"up ({total} diagnostics)"


def _read_docs_parity_status(path: Path) -> str:
    if not path.exists():
        return "missing artifact"

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return "empty artifact"

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        lowered = raw.lower()
        if "passed" in lowered:
            return "pass"
        if "failed" in lowered:
            return "fail"
        return "unknown"

    status = payload.get("status") if isinstance(payload, dict) else None
    if isinstance(status, str) and status.strip():
        return status.strip().lower()

    failures = payload.get("failures") if isinstance(payload, dict) else None
    if isinstance(failures, list):
        return "fail" if failures else "pass"

    return "unknown"


def _render_table_row(
    inventory_path: Path,
    unused_summary_path: Path,
    docs_parity_output_path: Path,
    coverage: float,
    undocumented: int,
    trend: str,
    parity_status: str,
) -> str:
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    inv_rel = inventory_path.relative_to(ROOT).as_posix()
    unused_rel = unused_summary_path.relative_to(ROOT).as_posix()
    parity_rel = docs_parity_output_path.relative_to(ROOT).as_posix()
    return (
        f"| `{timestamp}` | `{inv_rel}` | `{unused_rel}` | `{parity_rel}` ({parity_status}) "
        f"| {coverage:.2f}% | {undocumented} | {trend} |"
    )


def _replace_table(handoff_path: Path, new_row: str) -> None:
    text = handoff_path.read_text(encoding="utf-8")
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise ValueError(
            f"Missing required markers in {handoff_path}: '{START_MARKER}' and '{END_MARKER}'."
        )

    table = "\n".join(
        [
            START_MARKER,
            "| Snapshot generated (UTC) | Inventory artifact | Unused-code summary | Docs parity validator output | Coverage % | Undocumented count | Diagnostics trend |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            new_row,
            END_MARKER,
        ]
    )
    updated = text[:start] + table + text[end + len(END_MARKER) :]
    handoff_path.write_text(updated, encoding="utf-8")


def main() -> int:
    args = _parse_args()
    inventory_payload = json.loads(args.inventory.read_text(encoding="utf-8"))
    unused_payload = json.loads(args.unused_summary.read_text(encoding="utf-8"))

    coverage = _coverage_percent(inventory_payload)
    undocumented = _undocumented_count(inventory_payload)
    trend = _diagnostics_trend(unused_payload)
    parity_status = _read_docs_parity_status(args.docs_parity_output)
    row = _render_table_row(
        args.inventory.resolve(),
        args.unused_summary.resolve(),
        args.docs_parity_output.resolve(),
        coverage,
        undocumented,
        trend,
        parity_status,
    )
    _replace_table(args.handoff.resolve(), row)
    print(f"Updated script analytics handoff status table: {args.handoff}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
