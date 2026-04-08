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
    ordered_stages: tuple["OrderedStageSpec", ...]
    commands: tuple[CommandSpec, ...]


@dataclass(frozen=True)
class OrderedStageSpec:
    id: str
    stop_on_fail: bool
    commands: tuple[CommandSpec, ...]


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    timed_out: bool = False


MANIFEST_PATH = Path(__file__).resolve().parents[2] / "docs/process/quality_stage_commands.json"


def _load_stages() -> dict[str, StageSpec]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stages = manifest["stages"]

    def _to_command(spec: dict[str, object]) -> CommandSpec:
        if "run_if_paths" not in spec:
            return CommandSpec(command=str(spec["command"]), timeout_seconds=int(spec["timeout_seconds"]))
        return CommandSpec(
            command=str(spec["command"]),
            timeout_seconds=int(spec["timeout_seconds"]),
            run_if_paths=tuple(spec["run_if_paths"]),
        )

    loaded: dict[str, StageSpec] = {}
    for stage_name, stage_spec in stages.items():
        ordered_stage_specs: list[OrderedStageSpec] = []
        if "ordered_stages" in stage_spec:
            for ordered in stage_spec["ordered_stages"]:
                commands = tuple(_to_command(spec) for spec in ordered["commands"])
                ordered_stage_specs.append(
                    OrderedStageSpec(
                        id=str(ordered["id"]),
                        stop_on_fail=bool(ordered.get("stop_on_fail", True)),
                        commands=commands,
                    )
                )
        else:
            commands = tuple(_to_command(spec) for spec in stage_spec["commands"])
            ordered_stage_specs.append(
                OrderedStageSpec(id=f"{stage_name}-default", stop_on_fail=True, commands=commands)
            )

        loaded[stage_name] = StageSpec(
            ordered_stages=tuple(ordered_stage_specs),
            commands=tuple(command for ordered in ordered_stage_specs for command in ordered.commands),
        )

    return loaded


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


def _diff_files(revision_range: str) -> tuple[str, ...]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", revision_range],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ()
    return tuple(path.strip() for path in proc.stdout.splitlines() if path.strip())


def _qa_push_changed_files() -> tuple[str, ...]:
    # 1) Prefer staged files when running qa-push manually before commit.
    staged_files = _staged_files()
    if staged_files:
        return staged_files

    # 2) During pre-push (clean index), scope by commits ahead of upstream.
    upstream_proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if upstream_proc.returncode == 0:
        upstream_ref = upstream_proc.stdout.strip()
        if upstream_ref:
            ahead_files = _diff_files(f"{upstream_ref}...HEAD")
            if ahead_files:
                return ahead_files

    # 3) Fallback for no-upstream/local-only branches: last commit delta.
    return _diff_files("HEAD~1..HEAD")


def _command_relevant_for_paths(command: CommandSpec, changed_files: tuple[str, ...]) -> bool:
    if not command.run_if_paths:
        return True
    return any(fnmatch.fnmatch(path, pattern) for path in changed_files for pattern in command.run_if_paths)


def _select_commands(stage: str, stage_spec: StageSpec, *, full_stage: bool, changed_files: tuple[str, ...]) -> tuple[CommandSpec, ...]:
    if full_stage or stage not in {"qa-commit", "qa-push"} or not changed_files:
        return stage_spec.commands
    return tuple(spec for spec in stage_spec.commands if _command_relevant_for_paths(spec, changed_files))


def _select_ordered_stages(
    stage: str,
    stage_spec: StageSpec,
    *,
    full_stage: bool,
    changed_files: tuple[str, ...],
) -> tuple[OrderedStageSpec, ...]:
    selected: list[OrderedStageSpec] = []
    for ordered_stage in stage_spec.ordered_stages:
        commands = _select_commands(
            stage,
            StageSpec(ordered_stages=(ordered_stage,), commands=ordered_stage.commands),
            full_stage=full_stage,
            changed_files=changed_files,
        )
        if commands:
            selected.append(
                OrderedStageSpec(
                    id=ordered_stage.id,
                    stop_on_fail=ordered_stage.stop_on_fail,
                    commands=commands,
                )
            )
    return tuple(selected)


def _first_failing_files(output: str) -> list[str]:
    files: list[str] = []
    for match in FILE_RE.finditer(output):
        path = match.group("path")
        if path not in files:
            files.append(path)
        if len(files) >= 5:
            break
    return files


def _run_command(spec: CommandSpec) -> CommandResult:
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
        return CommandResult(returncode=124, timed_out=True)

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

    return CommandResult(returncode=proc.returncode)


def _emit_failure_reason(*, stage_id: str, reason_code: str, next_action: str) -> None:
    print(json.dumps({"stage_id": stage_id, "reason_code": reason_code, "next_action": next_action}))


def main() -> int:
    stages = _load_stages()
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=tuple(stages.keys()))
    parser.add_argument(
        "--full-stage",
        action="store_true",
        help="Run every command for the selected stage, ignoring staged-path filters.",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "local", "ci"),
        default="auto",
        help="Execution mode. 'local' disables CI env auto-detection, 'ci' forces full-stage behavior.",
    )
    args = parser.parse_args()

    ci_env_enabled = os.getenv("CI", "").lower() in {"1", "true", "yes"}
    full_stage = args.full_stage or args.mode == "ci" or (args.mode == "auto" and ci_env_enabled)
    changed_files: tuple[str, ...] = ()
    if args.stage == "qa-commit" and not full_stage:
        changed_files = _staged_files()
    elif args.stage == "qa-push" and not full_stage:
        changed_files = _qa_push_changed_files()

    selected_ordered_stages = _select_ordered_stages(
        args.stage,
        stages[args.stage],
        full_stage=full_stage,
        changed_files=changed_files,
    )

    print(f"QA stage: {args.stage}")
    if changed_files:
        print(f"Staged files considered for command selection: {', '.join(changed_files)}")
    elif args.stage in {"qa-commit", "qa-push"} and not full_stage:
        print("No changed files detected for stage filtering; falling back to full stage command set.")
    if full_stage:
        print("Stage mode: full")
    elif args.stage in {"qa-commit", "qa-push"}:
        print("Stage mode: staged-path filtered")

    if not selected_ordered_stages:
        print("No commands matched changed paths; stage passed without running commands.")
        return 0

    for ordered_stage in selected_ordered_stages:
        print(f"\n=== Ordered stage: {ordered_stage.id} (stop_on_fail={str(ordered_stage.stop_on_fail).lower()}) ===")
        for spec in ordered_stage.commands:
            result = _run_command(spec)
            if result.returncode == 0:
                continue
            _emit_failure_reason(
                stage_id=ordered_stage.id,
                reason_code="timeout" if result.timed_out else "command_failed",
                next_action=f"Rerun command locally: {spec.command}",
            )
            if ordered_stage.stop_on_fail:
                print(f"Stopping execution after blocking failure in ordered stage '{ordered_stage.id}'.")
                return result.returncode

    print(f"\nStage {args.stage} passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
