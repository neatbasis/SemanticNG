#!/usr/bin/env python3
"""Run deterministic QA stages with budgets and actionable failure output."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

FILE_RE = re.compile(r"(?P<path>[A-Za-z0-9_./-]+\.(?:py|pyi|yaml|yml|toml|json|md|txt))(?:[:(]|\s)")


@dataclass(frozen=True)
class CommandSpec:
    command: str
    timeout_seconds: int
    run_if_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class StageSpec:
    commands: tuple[CommandSpec, ...]


MANIFEST_PATH = Path(__file__).resolve().parents[2] / "docs/process/quality_stage_commands.json"


def _load_stages() -> dict[str, StageSpec]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stages = manifest["stages"]
    return {
        stage_name: StageSpec(
            commands=tuple(
                CommandSpec(command=spec["command"], timeout_seconds=int(spec["timeout_seconds"]))
                if "run_if_paths" not in spec
                else CommandSpec(
                    command=spec["command"],
                    timeout_seconds=int(spec["timeout_seconds"]),
                    run_if_paths=tuple(spec["run_if_paths"]),
                )
                for spec in stage_spec["commands"]
            )
        )
        for stage_name, stage_spec in stages.items()
    }


def _staged_files() -> tuple[str, ...]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "unable to read staged files")
    return tuple(path.strip() for path in proc.stdout.splitlines() if path.strip())


def _command_relevant_for_paths(command: CommandSpec, changed_files: tuple[str, ...]) -> bool:
    if not command.run_if_paths:
        return True
    return any(fnmatch.fnmatch(path, pattern) for path in changed_files for pattern in command.run_if_paths)


def _select_commands(stage: str, stage_spec: StageSpec, *, full_stage: bool, changed_files: tuple[str, ...]) -> tuple[CommandSpec, ...]:
    if full_stage or stage != "qa-commit" or not changed_files:
        return stage_spec.commands
    return tuple(spec for spec in stage_spec.commands if _command_relevant_for_paths(spec, changed_files))


def _first_failing_files(output: str) -> list[str]:
    files: list[str] = []
    for match in FILE_RE.finditer(output):
        path = match.group("path")
        if path not in files:
            files.append(path)
        if len(files) >= 5:
            break
    return files


def _run_command(spec: CommandSpec) -> int:
    print(f"\n▶ Running: {spec.command}")
    print(f"   Timeout budget: {spec.timeout_seconds}s")
    started = time.monotonic()
    try:
        proc = subprocess.run(
            spec.command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=spec.timeout_seconds,
        )
    except subprocess.TimeoutExpired as err:
        elapsed = time.monotonic() - started
        print(err.stdout or "", end="")
        print(err.stderr or "", end="", file=sys.stderr)
        print(f"\n✖ Timeout after {elapsed:.1f}s (budget {spec.timeout_seconds}s)")
        print(f"Rerun command: {spec.command}")
        return 124

    elapsed = time.monotonic() - started
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)

    if proc.returncode != 0:
        print(f"\n✖ Failed in {elapsed:.1f}s with exit code {proc.returncode}")
        print(f"Rerun command: {spec.command}")
        failing_files = _first_failing_files((proc.stdout or "") + "\n" + (proc.stderr or ""))
        if failing_files:
            print(f"First failing files: {', '.join(failing_files)}")
        else:
            print("First failing files: none detected from output")
    else:
        print(f"✔ Passed in {elapsed:.1f}s")

    return proc.returncode


def main() -> int:
    stages = _load_stages()
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=tuple(stages.keys()))
    parser.add_argument(
        "--full-stage",
        action="store_true",
        help="Run every command for the selected stage, ignoring staged-path filters.",
    )
    args = parser.parse_args()

    full_stage = args.full_stage or os.getenv("CI", "").lower() in {"1", "true", "yes"}
    changed_files: tuple[str, ...] = ()
    if args.stage == "qa-commit" and not full_stage:
        changed_files = _staged_files()

    selected_commands = _select_commands(
        args.stage,
        stages[args.stage],
        full_stage=full_stage,
        changed_files=changed_files,
    )

    print(f"QA stage: {args.stage}")
    if changed_files:
        print(f"Staged files considered for command selection: {', '.join(changed_files)}")
    elif args.stage == "qa-commit" and not full_stage:
        print("No staged files detected; falling back to full stage command set.")
    if full_stage:
        print("Stage mode: full")
    elif args.stage == "qa-commit":
        print("Stage mode: staged-path filtered")

    if not selected_commands:
        print("No commands matched changed paths; stage passed without running commands.")
        return 0

    for spec in selected_commands:
        code = _run_command(spec)
        if code != 0:
            return code

    print(f"\nStage {args.stage} passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
