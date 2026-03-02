#!/usr/bin/env python3
"""Validate parity between script entrypoint inventory and documentation catalog."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = ROOT / "docs/process/script_entrypoints_inventory.json"
DEFAULT_CATALOG = ROOT / "docs/process/script_entrypoints_catalog.md"


ROW_RE = re.compile(r"^\|\s*`(?P<path>[^`]+)`\s*\|\s*(?P<purpose>.*?)\s*\|\s*(?P<invoked>.*?)\s*\|\s*(?P<owner>.*?)\s*\|\s*(?P<doc>.*?)\s*\|\s*$")


def _load_inventory(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["entrypoint_path"]: row for row in payload}


def _split_cell(cell: str) -> list[str]:
    if not cell.strip():
        return []
    return [p.strip() for p in cell.split("<br>") if p.strip()]


def _load_catalog(path: Path) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        m = ROW_RE.match(line)
        if not m:
            continue
        entry_path = m.group("path")
        if entry_path in rows:
            raise ValueError(f"Duplicate catalog row for {entry_path} at line {line_no}")
        rows[entry_path] = {
            "line": line_no,
            "invoked_from": _split_cell(m.group("invoked")),
            "owner": _split_cell(m.group("owner")),
            "doc": m.group("doc").strip(),
        }
    return rows


def _compute_owners(invoked_from: list[str]) -> list[str]:
    owners: set[str] = set()
    for source in invoked_from:
        if source.startswith("workflow:"):
            workflow_path = source.split(":", 2)[1]
            owners.add(f"workflow:{Path(workflow_path).stem}")
        elif source.startswith("quality_stage:"):
            owners.add(":".join(source.split(":")[:2]))
        elif source.startswith("precommit:"):
            owners.add(":".join(source.split(":")[:2]))
        elif source.startswith("make:"):
            owners.add(":".join(source.split(":")[:2]))
    return sorted(owners)


def _target_exists(makefile_text: str, target: str) -> bool:
    needle = f"{target}:"
    for line in makefile_text.splitlines():
        if line.startswith((" ", "\t", ".")):
            continue
        if line.startswith(needle):
            return True
    return False


def _hook_exists(precommit_text: str, hook_id: str) -> bool:
    return bool(re.search(rf"^\s*-\s+id:\s*{re.escape(hook_id)}\s*$", precommit_text, flags=re.MULTILINE))


def _validate_entrypoint_exists(root: Path, entrypoint: str, makefile_text: str, precommit_text: str) -> str | None:
    if entrypoint.startswith("Makefile:"):
        target = entrypoint.split(":", 1)[1]
        if not _target_exists(makefile_text, target):
            return f"Make target missing: {entrypoint}"
        return None
    if entrypoint.startswith("hook:"):
        hook_id = entrypoint.split(":", 1)[1]
        if not _hook_exists(precommit_text, hook_id):
            return f"Pre-commit hook missing: {entrypoint}"
        return None

    path = root / entrypoint
    if not path.exists():
        return f"File missing: {entrypoint}"
    return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = args.root.resolve()
    inventory = _load_inventory(args.inventory)
    catalog = _load_catalog(args.catalog)

    failures: list[str] = []

    missing_rows = sorted(set(inventory) - set(catalog))
    if missing_rows:
        failures.append("Missing catalog rows for inventory entrypoints:\n  - " + "\n  - ".join(missing_rows))

    extra_rows = sorted(set(catalog) - set(inventory))
    if extra_rows:
        failures.append("Catalog rows with no matching inventory entrypoint:\n  - " + "\n  - ".join(extra_rows))

    makefile_text = (root / "Makefile").read_text(encoding="utf-8") if (root / "Makefile").exists() else ""
    precommit_text = (root / ".pre-commit-config.yaml").read_text(encoding="utf-8") if (root / ".pre-commit-config.yaml").exists() else ""

    for entrypoint, row in catalog.items():
        issue = _validate_entrypoint_exists(root, entrypoint, makefile_text, precommit_text)
        if issue:
            failures.append(issue)

        if entrypoint not in inventory:
            continue

        expected_invoked = sorted(inventory[entrypoint]["invoked_from"])
        got_invoked = sorted(row["invoked_from"])
        if expected_invoked != got_invoked:
            failures.append(
                f"Invocation drift for {entrypoint}: expected {expected_invoked} but found {got_invoked}"
            )

        expected_owners = _compute_owners(expected_invoked)
        got_owners = sorted(row["owner"])
        if expected_owners != got_owners:
            failures.append(f"Owner drift for {entrypoint}: expected {expected_owners} but found {got_owners}")

    if failures:
        print("Script docs parity validation failed:", file=sys.stderr)
        for item in failures:
            print(f"- {item}", file=sys.stderr)
        return 1

    print("Script docs parity validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
