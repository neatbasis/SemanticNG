#!/usr/bin/env python3
"""Render a PR-ready transition evidence block for milestone governance checks."""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs" / "dod_manifest.json"
PR_TEMPLATE_PATH = ROOT / ".github" / "pull_request_template.md"
AUTOGEN_BEGIN = "<!-- BEGIN AUTOGEN: capability-examples -->"
AUTOGEN_END = "<!-- END AUTOGEN: capability-examples -->"


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


def _commands_for_pr_template_examples(manifest: dict) -> dict[str, list[str]]:
    commands_by_capability: dict[str, list[str]] = {}
    for capability in manifest.get("capabilities", []):
        cap_id = capability.get("id")
        if not isinstance(cap_id, str) or not cap_id.strip():
            continue

        pytest_commands = capability.get("pytest_commands") or []
        commands = [command for command in pytest_commands if isinstance(command, str) and command.strip()]
        if commands:
            commands_by_capability[cap_id] = commands

    return commands_by_capability


def _render_pr_template_examples(manifest: dict) -> str:
    lines: list[str] = ["```text"]
    commands_by_capability = _commands_for_pr_template_examples(manifest)
    for cap_id in sorted(commands_by_capability):
        lines.append(f"# Capability: {cap_id}")
        for command in commands_by_capability[cap_id]:
            lines.append(command)
            lines.append("https://github.com/<org>/<repo>/actions/runs/<run_id>")
            lines.append("")

    lines.append("```")
    return "\n".join(lines).rstrip() + "\n"


def _render_pr_template_autogen_section(manifest: dict) -> str:
    body = _render_pr_template_examples(manifest).rstrip("\n")
    return f"{AUTOGEN_BEGIN}\n{body}\n{AUTOGEN_END}"


def _replace_between_markers(text: str, replacement: str) -> str:
    start = text.find(AUTOGEN_BEGIN)
    end = text.find(AUTOGEN_END)
    if start == -1 or end == -1 or end < start:
        raise ValueError("Failed to locate AUTOGEN markers in pull request template")

    end += len(AUTOGEN_END)
    return f"{text[:start]}{replacement}{text[end:]}"


def regenerate_pr_template_autogen_section() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    template = PR_TEMPLATE_PATH.read_text(encoding="utf-8")
    updated = _replace_between_markers(template, _render_pr_template_autogen_section(manifest))
    PR_TEMPLATE_PATH.write_text(updated, encoding="utf-8")


def check_pr_template_autogen_section() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    template = PR_TEMPLATE_PATH.read_text(encoding="utf-8")
    expected_template = _replace_between_markers(template, _render_pr_template_autogen_section(manifest))

    if template == expected_template:
        print("PR template AUTOGEN section is up to date.")
        return 0

    diff = difflib.unified_diff(
        template.splitlines(),
        expected_template.splitlines(),
        fromfile=str(PR_TEMPLATE_PATH),
        tofile=f"{PR_TEMPLATE_PATH} (expected)",
        lineterm="",
    )
    print("PR template AUTOGEN section is stale. Regenerate it with:")
    print("  python .github/scripts/render_transition_evidence.py --regenerate-pr-template")
    print("\n".join(diff))
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Base commit SHA")
    parser.add_argument("--head", help="Head commit SHA")
    parser.add_argument(
        "--regenerate-pr-template",
        action="store_true",
        help="Regenerate the pull_request_template.md capability examples autogen block",
    )
    parser.add_argument(
        "--check-pr-template-autogen",
        action="store_true",
        help="Fail if the pull_request_template.md capability examples autogen block is stale",
    )
    parser.add_argument(
        "--emit-pr-template-autogen",
        action="store_true",
        help="Print the rendered pull_request_template.md capability examples autogen block",
    )
    args = parser.parse_args()

    if args.regenerate_pr_template:
        regenerate_pr_template_autogen_section()
        return 0

    if args.check_pr_template_autogen:
        return check_pr_template_autogen_section()

    if args.emit_pr_template_autogen:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        print(_render_pr_template_autogen_section(manifest))
        return 0

    if not args.base or not args.head:
        parser.error("--base and --head are required unless --regenerate-pr-template is provided")

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
