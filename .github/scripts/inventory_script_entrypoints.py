#!/usr/bin/env python3
"""Generate a static inventory of script entrypoints and where they are invoked."""

from __future__ import annotations

import argparse
import json
import shlex
from collections import defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs" / "process" / "script_entrypoints_inventory.json"
SCRIPT_DIRS = (".github/scripts", "scripts/ci", "scripts/dev")


def _entrypoint_type(path: str) -> str:
    if path.startswith("Makefile:"):
        return "make_target"
    if path.endswith(".py"):
        return "python_script"
    if path.endswith(".sh"):
        return "shell_script"
    return "workflow_inline_run"


def _tokenize_command(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _extract_script_paths(command: str) -> set[str]:
    tokens = _tokenize_command(command)
    results: set[str] = set()
    for token in tokens:
        candidate = token.strip()
        if candidate.startswith("./"):
            candidate = candidate[2:]
        if candidate.startswith((".github/scripts/", "scripts/ci/", "scripts/dev/")) and candidate.endswith((".py", ".sh")):
            results.add(candidate)
    return results


def _extract_make_targets(command: str) -> set[str]:
    tokens = _tokenize_command(command)
    targets: set[str] = set()
    for idx, token in enumerate(tokens):
        if token in {"make", "$(MAKE)"}:
            for next_token in tokens[idx + 1 :]:
                if next_token.startswith("-") or "=" in next_token:
                    continue
                targets.add(f"Makefile:{next_token}")
                break
    return targets


def _add_invocation(invocations: dict[str, set[str]], entrypoint: str, source: str) -> None:
    invocations[entrypoint].add(source)


def _scan_filesystem_entrypoints(root: Path, invocations: dict[str, set[str]]) -> None:
    for rel_dir in SCRIPT_DIRS:
        base = root / rel_dir
        if not base.exists():
            continue
        for path in sorted(base.glob("*")):
            if path.suffix not in {".py", ".sh"}:
                continue
            _add_invocation(invocations, path.relative_to(root).as_posix(), "filesystem_scan")


def _extract_workflow_run_commands(workflow_path: Path) -> Iterable[tuple[int, str]]:
    lines = workflow_path.read_text(encoding="utf-8").splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.lstrip()
        if stripped.startswith('- '):
            stripped = stripped[2:].lstrip()
        if not stripped.startswith("run:"):
            idx += 1
            continue

        indent = len(line) - len(stripped)
        rhs = stripped[4:].strip()
        line_number = idx + 1

        if rhs in {"|", ">", "|-", ">-", "|+", ">+"}:
            idx += 1
            while idx < len(lines):
                block_line = lines[idx]
                block_stripped = block_line.lstrip()
                block_indent = len(block_line) - len(block_stripped)
                if block_stripped and block_indent <= indent:
                    break
                if block_stripped:
                    yield idx + 1, block_stripped
                idx += 1
            continue

        if rhs:
            yield line_number, rhs
        idx += 1


def _scan_workflows(root: Path, invocations: dict[str, set[str]]) -> None:
    workflows_dir = root / ".github" / "workflows"
    for workflow in sorted(workflows_dir.glob("*.yml")):
        rel_workflow = workflow.relative_to(root).as_posix()
        for line_no, command in _extract_workflow_run_commands(workflow):
            source = f"workflow:{rel_workflow}:L{line_no}"
            for entrypoint in _extract_script_paths(command):
                _add_invocation(invocations, entrypoint, source)
            for make_target in _extract_make_targets(command):
                _add_invocation(invocations, make_target, source)


def _scan_precommit(root: Path, invocations: dict[str, set[str]]) -> None:
    config = root / ".pre-commit-config.yaml"
    if not config.exists():
        return

    current_hook: str | None = None
    for line_no, line in enumerate(config.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("- id:"):
            current_hook = stripped.split(":", 1)[1].strip()
            continue
        if not stripped.startswith("entry:"):
            continue
        entry = stripped.split(":", 1)[1].strip()
        hook = current_hook or "<unknown>"
        source = f"precommit:{hook}:L{line_no}"
        for entrypoint in _extract_script_paths(entry):
            _add_invocation(invocations, entrypoint, source)
        for make_target in _extract_make_targets(entry):
            _add_invocation(invocations, make_target, source)
        if _extract_script_paths(entry):
            _add_invocation(invocations, f"hook:{hook}", source)


def _scan_makefile(root: Path, invocations: dict[str, set[str]]) -> None:
    makefile = root / "Makefile"
    if not makefile.exists():
        return

    current_target: str | None = None
    for line_no, line in enumerate(makefile.read_text(encoding="utf-8").splitlines(), start=1):
        if line and not line.startswith(("\t", " ")) and ":" in line and not line.startswith("."):
            current_target = line.split(":", 1)[0].strip()
            continue
        stripped = line.lstrip("\t").lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if current_target is None:
            continue

        if stripped.startswith("@"):
            stripped = stripped[1:].strip()

        source = f"make:{current_target}:L{line_no}"
        for entrypoint in _extract_script_paths(stripped):
            _add_invocation(invocations, entrypoint, source)
        for make_target in _extract_make_targets(stripped):
            _add_invocation(invocations, make_target, source)


def _scan_quality_manifest(root: Path, invocations: dict[str, set[str]]) -> None:
    manifest_path = root / "docs" / "process" / "quality_stage_commands.json"
    if not manifest_path.exists():
        return

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    stages = payload.get("stages", {})
    if not isinstance(stages, dict):
        return

    for stage_name, stage_value in stages.items():
        if not isinstance(stage_value, dict):
            continue
        commands = stage_value.get("commands", [])
        if isinstance(commands, list):
            for idx, command_spec in enumerate(commands):
                if not isinstance(command_spec, dict):
                    continue
                command = command_spec.get("command")
                if not isinstance(command, str):
                    continue
                source = f"quality_stage:{stage_name}:commands[{idx}]"
                for entrypoint in _extract_script_paths(command):
                    _add_invocation(invocations, entrypoint, source)
                for make_target in _extract_make_targets(command):
                    _add_invocation(invocations, make_target, source)

        precommit_hook = stage_value.get("precommit_hook")
        if isinstance(precommit_hook, dict):
            entry = precommit_hook.get("entry")
            if isinstance(entry, str):
                source = f"quality_stage:{stage_name}:precommit_hook"
                for entrypoint in _extract_script_paths(entry):
                    _add_invocation(invocations, entrypoint, source)


def build_inventory(root: Path) -> list[dict[str, object]]:
    invocations: dict[str, set[str]] = defaultdict(set)
    _scan_filesystem_entrypoints(root, invocations)
    _scan_workflows(root, invocations)
    _scan_precommit(root, invocations)
    _scan_makefile(root, invocations)
    _scan_quality_manifest(root, invocations)

    rows: list[dict[str, object]] = []
    for entrypoint in sorted(invocations):
        if entrypoint.startswith("hook:"):
            entrypoint_type = "precommit_hook"
        else:
            entrypoint_type = _entrypoint_type(entrypoint)
        rows.append(
            {
                "entrypoint_path": entrypoint,
                "entrypoint_type": entrypoint_type,
                "invoked_from": sorted(invocations[entrypoint]),
                "documented": False,
            }
        )
    return rows


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Inventory json path.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    inventory = build_inventory(args.root.resolve())
    args.output.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
