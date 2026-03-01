#!/usr/bin/env python3
"""Compare workflow run commands against documented policy sources and flag drift."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "docs" / "workflow_command_policy.json"


@dataclass(frozen=True)
class PolicyCommand:
    command: str
    workflows: tuple[str, ...]
    policy_sources: tuple[str, ...]


def _load_policy(path: Path) -> tuple[PolicyCommand, ...]:
    data = json.loads(path.read_text(encoding="utf-8"))
    commands: list[PolicyCommand] = []
    for entry in data.get("required_commands", []):
        if not isinstance(entry, dict):
            continue
        command = entry.get("command")
        workflows = entry.get("workflows")
        policy_sources = entry.get("policy_sources")
        if not isinstance(command, str) or not command.strip():
            continue
        if not isinstance(workflows, list) or not all(isinstance(item, str) for item in workflows):
            continue
        if not isinstance(policy_sources, list) or not all(isinstance(item, str) for item in policy_sources):
            continue
        commands.append(
            PolicyCommand(
                command=command.strip(),
                workflows=tuple(workflows),
                policy_sources=tuple(policy_sources),
            )
        )
    return tuple(commands)


def _workflow_has_command(workflow_path: Path, command: str) -> bool:
    workflow_text = workflow_path.read_text(encoding="utf-8")
    return command in workflow_text


def generate_report(policy_path: Path) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    coverage: list[str] = []
    for policy_command in _load_policy(policy_path):
        coverage.append(
            "Command policy: "
            f"`{policy_command.command}` sourced from {', '.join(policy_command.policy_sources)}"
        )
        for workflow in policy_command.workflows:
            workflow_path = ROOT / workflow
            if not workflow_path.exists():
                missing.append(
                    f"{workflow}: workflow file missing; cannot validate command `{policy_command.command}`."
                )
                continue
            if not _workflow_has_command(workflow_path, policy_command.command):
                missing.append(
                    f"{workflow}: missing required command `{policy_command.command}` "
                    f"(policy sources: {', '.join(policy_command.policy_sources)})."
                )
    return missing, coverage


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--summary", action="store_true", help="Emit markdown summary for CI job summary.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    missing, coverage = generate_report(args.policy)

    if args.summary:
        print("## Workflow policy drift report")
        for line in coverage:
            print(f"- {line}")
        if missing:
            print("- Drift detected:")
            for issue in missing:
                print(f"  - {issue}")
        else:
            print("- No workflow-policy drift detected.")

    if missing:
        print("Workflow policy drift detected:")
        for issue in missing:
            print(f"  - {issue}")
        return 1

    print("Workflow policy drift check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
