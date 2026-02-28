#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def _load_manifest(rev: str) -> dict:
    raw = subprocess.check_output(["git", "show", f"{rev}:docs/dod_manifest.json"], text=True)
    return json.loads(raw)


def _status_transitions(base_manifest: dict, head_manifest: dict) -> dict[str, tuple[str, str]]:
    base = {cap["id"]: cap for cap in base_manifest.get("capabilities", [])}
    out: dict[str, tuple[str, str]] = {}
    for cap in head_manifest.get("capabilities", []):
        cap_id = cap.get("id")
        if cap_id not in base:
            continue
        before = base[cap_id].get("status")
        after = cap.get("status")
        if before != after:
            out[cap_id] = (str(before), str(after))
    return out


def _transition_commands(head_manifest: dict, transitioned: set[str]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for cap in head_manifest.get("capabilities", []):
        cap_id = cap.get("id")
        if cap_id not in transitioned:
            continue
        for command in cap.get("pytest_commands", []):
            if isinstance(command, str) and command.strip():
                rows.append((str(cap_id), command))
    return rows


def _render_lines(rows: list[tuple[str, str]]) -> list[str]:
    if not rows:
        return ["(No status transitions detected between selected revisions.)"]
    lines = ["## Milestone pytest commands + adjacent evidence URLs (mandatory)", ""]
    current = None
    for cap_id, command in rows:
        if cap_id != current:
            if current is not None:
                lines.append("")
            lines.append(f"# Capability: {cap_id}")
            current = cap_id
        lines.append(command)
        lines.append("Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Render exact PR evidence block for transitioned capabilities.")
    parser.add_argument("--base", required=True, help="Base git revision (e.g., origin/main SHA)")
    parser.add_argument("--head", required=True, help="Head git revision (e.g., current HEAD SHA)")
    parser.add_argument(
        "--as-pr-body-json",
        action="store_true",
        help="Emit a minimal GitHub event payload JSON with pull_request.body populated.",
    )
    args = parser.parse_args()

    base_manifest = _load_manifest(args.base)
    head_manifest = _load_manifest(args.head)
    transitioned = set(_status_transitions(base_manifest, head_manifest))
    lines = _render_lines(_transition_commands(head_manifest, transitioned))
    body = "\n".join(lines)

    if args.as_pr_body_json:
        print(json.dumps({"pull_request": {"body": body}}))
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
