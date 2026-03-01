#!/usr/bin/env python3
"""Select and run milestone-gate pytest commands from manifest-driven rules."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _matches_path(changed_file: str, configured_path: str) -> bool:
    normalized = configured_path.rstrip("/")
    return changed_file == normalized or changed_file.startswith(f"{normalized}/")


def _matches_code_path(changed_file: str, code_path: str) -> bool:
    normalized = code_path.rstrip("/")
    return changed_file == normalized or changed_file.startswith(f"{normalized}/")


def _dedupe(commands: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for command in commands:
        if command in seen:
            continue
        seen.add(command)
        ordered.append(command)
    return ordered


def _is_docs_only_change(changed_files: list[str], filters: dict[str, Any]) -> bool:
    if not changed_files:
        return False
    prefixes = filters.get("docs_only_prefixes", [])
    allowlist = set(filters.get("docs_only_allowlist", []))
    for path in changed_files:
        if path in allowlist:
            continue
        if any(path.startswith(prefix) for prefix in prefixes):
            continue
        return False
    return True


def _touches_impacting_docs(changed_files: list[str], filters: dict[str, Any]) -> bool:
    impacting = filters.get("impacting_docs_paths", [])
    return any(_matches_path(path, configured) for path in changed_files for configured in impacting)


def select_milestone_commands(
    *, changed_files: list[str], head_manifest: dict[str, Any], base_manifest: dict[str, Any], surface_manifest: dict[str, Any]
) -> dict[str, Any]:
    capabilities = head_manifest.get("capabilities", [])
    filters = surface_manifest.get("change_scope_filters", {})

    docs_only = _is_docs_only_change(changed_files, filters)
    impacting_docs = _touches_impacting_docs(changed_files, filters)
    touches_state_renorm = any(path.startswith("src/state_renormalization/") for path in changed_files)
    manifest_changed = "docs/dod_manifest.json" in changed_files

    commands: list[str] = []
    reasons: dict[str, list[str]] = {}
    skipped_as_covered: list[str] = []

    # Milestone-targeted delta suites.
    if not docs_only or impacting_docs:
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
            if not capability_changed:
                continue
            for command in capability.get("pytest_commands", []):
                commands.append(command)
                reasons.setdefault(command, []).append(
                    f"milestone_targeted_delta:{capability.get('id', 'unknown')}"
                )

    # Transition-only suites.
    base_by_id = {cap.get("id"): cap for cap in base_manifest.get("capabilities", [])}
    for head_capability in capabilities:
        capability_id = head_capability.get("id")
        if not capability_id:
            continue
        base_capability = base_by_id.get(capability_id)
        if not base_capability:
            continue
        if base_capability.get("status") == "in_progress" and head_capability.get("status") == "done":
            for command in head_capability.get("pytest_commands", []):
                commands.append(command)
                reasons.setdefault(command, []).append(f"transition_only:{capability_id}")

    deduped = _dedupe(commands)

    baseline_covered = set(surface_manifest.get("baseline", {}).get("guaranteed_pytest_commands", []))
    selected: list[str] = []
    for command in deduped:
        if command in baseline_covered:
            skipped_as_covered.append(command)
            continue
        selected.append(command)

    return {
        "changed_files": changed_files,
        "docs_only_change": docs_only,
        "impacting_docs_change": impacting_docs,
        "selected_commands": selected,
        "selection_reasons": {cmd: reasons.get(cmd, []) for cmd in selected},
        "skipped_already_covered": _dedupe(skipped_as_covered),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_manifest_at(ref: str, path: str) -> dict[str, Any]:
    output = subprocess.check_output(["git", "show", f"{ref}:{path}"], text=True)
    return json.loads(output)


def _changed_files(base_sha: str, head_sha: str) -> list[str]:
    output = subprocess.check_output(["git", "diff", "--name-only", base_sha, head_sha], text=True)
    return [line.strip() for line in output.splitlines() if line.strip()]


def _render_summary(selection: dict[str, Any]) -> str:
    lines = ["## Milestone command selection", "", "### Selected commands"]
    selected = selection.get("selected_commands", [])
    if selected:
        for command in selected:
            reasons = ", ".join(selection.get("selection_reasons", {}).get(command, [])) or "unspecified"
            lines.append(f"- `{command}`")
            lines.append(f"  - why: {reasons}")
    else:
        lines.append("- none")

    lines.extend(["", "### Skipped as already covered by baseline"])
    skipped = selection.get("skipped_already_covered", [])
    if skipped:
        for command in skipped:
            lines.append(f"- `{command}`")
    else:
        lines.append("- none")

    lines.extend(["", "### Scope filters", f"- docs_only_change: `{selection.get('docs_only_change')}`"])
    lines.append(f"- impacting_docs_change: `{selection.get('impacting_docs_change')}`")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--surface-manifest", default=".github/test_surface_manifest.json")
    parser.add_argument("--dod-manifest", default="docs/dod_manifest.json")
    parser.add_argument("--output-json", default="artifacts/milestone_test_selection.json")
    parser.add_argument("--summary", default="artifacts/milestone_test_selection_summary.md")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    changed_files = _changed_files(args.base, args.head)
    head_manifest = _read_json(Path(args.dod_manifest))
    base_manifest = _read_manifest_at(args.base, args.dod_manifest)
    surface_manifest = _read_json(Path(args.surface_manifest))

    selection = select_milestone_commands(
        changed_files=changed_files,
        head_manifest=head_manifest,
        base_manifest=base_manifest,
        surface_manifest=surface_manifest,
    )

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")

    summary = _render_summary(selection)
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary + "\n", encoding="utf-8")

    print(summary)

    if not args.run:
        return 0

    for command in selection.get("selected_commands", []):
        print(f"\n>>> Running: {command}")
        completed = subprocess.run(command, shell=True)
        if completed.returncode != 0:
            return completed.returncode

    print("\nMilestone-selected commands completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
