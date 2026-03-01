#!/usr/bin/env python3
"""Run governance-targeted pytest commands for staged changes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _matches_code_path(changed_file: str, code_path: str) -> bool:
    normalized = code_path.rstrip("/")
    return changed_file == normalized or changed_file.startswith(f"{normalized}/")


def _dedupe(commands: list[str]) -> list[str]:
    deduped_commands: list[str] = []
    seen: set[str] = set()
    for command in commands:
        if command in seen:
            continue
        seen.add(command)
        deduped_commands.append(command)
    return deduped_commands


def select_governance_commands(
    changed_files: list[str],
    head_manifest: dict,
    base_manifest: dict | None = None,
) -> list[str]:
    """Select pytest commands relevant to the changed staged files."""
    capabilities = head_manifest.get("capabilities", [])

    touches_state_renorm = any(
        path.startswith("src/state_renormalization/") for path in changed_files
    )
    manifest_changed = "docs/dod_manifest.json" in changed_files

    commands: list[str] = []

    for capability in capabilities:
        if capability.get("status") != "in_progress":
            continue

        capability_paths = capability.get("code_paths", [])
        capability_changed = (
            touches_state_renorm
            or manifest_changed
            or any(
                _matches_code_path(changed, code_path)
                for changed in changed_files
                for code_path in capability_paths
            )
        )

        if capability_changed:
            commands.extend(capability.get("pytest_commands", []))

    if base_manifest is not None:
        base_by_id = {cap["id"]: cap for cap in base_manifest.get("capabilities", [])}
        head_by_id = {cap["id"]: cap for cap in capabilities}

        transitioned_to_done = []
        for capability_id, head_capability in head_by_id.items():
            base_capability = base_by_id.get(capability_id)
            if not base_capability:
                continue
            if (
                base_capability.get("status") == "in_progress"
                and head_capability.get("status") == "done"
            ):
                transitioned_to_done.append(head_capability)

        if transitioned_to_done:
            docs_updated = any(
                path == "README.md"
                or (path.startswith("docs/") and path != "docs/dod_manifest.json")
                for path in changed_files
            )
            if not docs_updated:
                raise ValueError(
                    "Detected in_progress -> done transition without non-manifest documentation updates. "
                    "Update README.md and/or docs/*.md alongside status transitions."
                )

            for capability in transitioned_to_done:
                commands.extend(capability.get("pytest_commands", []))

    return _dedupe(commands)


def _staged_files() -> list[str]:
    output = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        text=True,
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def _read_manifest(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_head_manifest() -> dict | None:
    try:
        output = subprocess.check_output(["git", "show", "HEAD:docs/dod_manifest.json"], text=True)
    except subprocess.CalledProcessError:
        return None
    return json.loads(output)


def main() -> int:
    changed_files = _staged_files()

    if not changed_files:
        print("No staged files; skipping governance pre-commit checks.")
        return 0

    print("Staged files:")
    for path in changed_files:
        print(f"  - {path}")

    head_manifest = _read_manifest("docs/dod_manifest.json")
    base_manifest = _read_head_manifest()

    try:
        commands = select_governance_commands(changed_files, head_manifest, base_manifest)
    except ValueError as error:
        print(str(error))
        return 1

    if not commands:
        print("No relevant governance pytest commands for staged changes.")
        return 0

    for command in commands:
        print(f"\n>>> Running: {command}")
        completed = subprocess.run(command, shell=True)
        if completed.returncode != 0:
            return completed.returncode

    print("\nAll selected governance pytest commands passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
