#!/usr/bin/env python3
"""Run deterministic QA stages with budgets and actionable failure output."""

from __future__ import annotations

import argparse
import json
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


MANIFEST_PATH = Path(__file__).resolve().parents[2] / "docs/process/quality_stage_commands.json"


def _load_stages() -> dict[str, list[CommandSpec]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stages = manifest["stages"]
    return {
        stage_name: [
            CommandSpec(command=spec["command"], timeout_seconds=int(spec["timeout_seconds"]))
            for spec in stage_spec["commands"]
        ]
        for stage_name, stage_spec in stages.items()
    }


STAGES = _load_stages()


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
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=tuple(STAGES.keys()))
    args = parser.parse_args()

    print(f"QA stage: {args.stage}")
    for spec in STAGES[args.stage]:
        code = _run_command(spec)
        if code != 0:
            return code

    print(f"\nStage {args.stage} passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
