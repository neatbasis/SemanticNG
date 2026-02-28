#!/usr/bin/env python3
"""Render a PR-ready transition evidence block for milestone governance checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def _load_manifest(rev: str) -> dict:
    raw = subprocess.check_output(["git", "show", f"{rev}:docs/dod_manifest.json"], text=True)
    return json.loads(raw)


def _status_transitions(base_manifest: dict, head_manifest: dict) -> set[str]:
    base = {cap["id"]: cap for cap in base_manifest.get("capabilities", [])}
    transitioned: set[str] = set()

    for capability in head_manifest.get("capabilities", []):
        cap_id = capability.get("id")
        if cap_id not in base:
            continue
        if base[cap_id].get("status") != capability.get("status"):
            transitioned.add(cap_id)

    return transitioned


def _transitioned_capability_commands(head_manifest: dict, transitioned_cap_ids: set[str]) -> dict[str, list[str]]:
    commands_by_capability: dict[str, list[str]] = {}
    for capability in head_manifest.get("capabilities", []):
        cap_id = capability.get("id")
        if cap_id not in transitioned_cap_ids:
            continue

        pytest_commands = capability.get("pytest_commands") or []
        commands = [command for command in pytest_commands if isinstance(command, str) and command.strip()]
        commands_by_capability[cap_id] = commands

    return commands_by_capability


def _render_block(commands_by_capability: dict[str, list[str]]) -> str:
    lines: list[str] = []
    lines.append("<!-- transition-evidence:start -->")
    lines.append("### Transition evidence (copy into PR description)")
    lines.append("")

    if not commands_by_capability:
        lines.append("No capability status transitions were detected for this diff.")
        lines.append("<!-- transition-evidence:end -->")
        return "\n".join(lines)

    lines.append("Replace each placeholder URL with the corresponding CI/test evidence URL.")
    lines.append("")
    for cap_id, commands in sorted(commands_by_capability.items()):
        lines.append(f"#### {cap_id}")
        if not commands:
            lines.append("(No pytest commands are defined for this transitioned capability.)")
            lines.append("")
            continue

        for idx, command in enumerate(commands, start=1):
            lines.append(command)
            lines.append(f"Evidence: https://example.com/replace-with-evidence/{cap_id}/{idx}")
            lines.append("")

    lines.append("<!-- transition-evidence:end -->")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base commit SHA")
    parser.add_argument("--head", required=True, help="Head commit SHA")
    args = parser.parse_args()

    try:
        base_manifest = _load_manifest(args.base)
        head_manifest = _load_manifest(args.head)
    except subprocess.CalledProcessError as exc:
        print(f"Failed to load docs/dod_manifest.json from git revisions: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Failed to parse docs/dod_manifest.json: {exc}", file=sys.stderr)
        return 1

    transitioned = _status_transitions(base_manifest, head_manifest)
    commands_by_capability = _transitioned_capability_commands(head_manifest, transitioned)
    print(_render_block(commands_by_capability), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
