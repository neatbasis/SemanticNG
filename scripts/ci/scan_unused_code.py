#!/usr/bin/env python3
"""Deterministically scan unused-code signals and emit CI artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "unused_code"

RUFF_RULES = "F401,F841"


@dataclass(frozen=True)
class Surface:
    name: str
    path: str
    blocking: bool


SURFACES: tuple[Surface, ...] = (
    Surface(name="core", path="src/core", blocking=True),
    Surface(name="state_renormalization", path="src/state_renormalization", blocking=True),
    Surface(name="features", path="src/features", blocking=False),
)


def _run_ruff(surface: Surface) -> tuple[list[dict[str, object]], str]:
    cmd = [
        "ruff",
        "check",
        "--select",
        RUFF_RULES,
        "--output-format",
        "json",
        surface.path,
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)

    stdout = proc.stdout.strip()
    if proc.returncode not in {0, 1}:
        raise RuntimeError(
            f"ruff failed for {surface.path} with exit code {proc.returncode}: {proc.stderr.strip() or stdout}"
        )

    diagnostics: list[dict[str, object]] = json.loads(stdout) if stdout else []
    diagnostics.sort(
        key=lambda item: (
            str(item.get("filename", "")),
            int(item.get("location", {}).get("row", 0)),
            int(item.get("location", {}).get("column", 0)),
            str(item.get("code", "")),
            str(item.get("message", "")),
        )
    )
    return diagnostics, " ".join(cmd)


def main() -> int:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    has_blocking_findings = False
    summary: list[dict[str, object]] = []

    for surface in SURFACES:
        diagnostics, command_text = _run_ruff(surface)
        payload = {
            "surface": surface.name,
            "path": surface.path,
            "blocking": surface.blocking,
            "scan_command": command_text,
            "rule_set": RUFF_RULES,
            "diagnostic_count": len(diagnostics),
            "diagnostics": diagnostics,
        }

        report_path = ARTIFACTS_DIR / f"{surface.name}_unused.json"
        report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        if surface.blocking and diagnostics:
            has_blocking_findings = True
            print(
                f"BLOCKING: {surface.path} has {len(diagnostics)} unused-code diagnostics "
                f"(artifact: {report_path.relative_to(ROOT)})"
            )
        elif diagnostics:
            print(
                f"WARNING: {surface.path} has {len(diagnostics)} unused-code diagnostics "
                f"(non-blocking; artifact: {report_path.relative_to(ROOT)})"
            )
        else:
            print(f"OK: {surface.path} has no unused-code diagnostics (artifact: {report_path.relative_to(ROOT)})")

        summary.append(
            {
                "surface": surface.name,
                "path": surface.path,
                "blocking": surface.blocking,
                "diagnostic_count": len(diagnostics),
                "artifact": str(report_path.relative_to(ROOT)),
            }
        )

    summary_path = ARTIFACTS_DIR / "summary.json"
    summary_path.write_text(json.dumps({"surfaces": summary}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote deterministic unused-code summary: {summary_path.relative_to(ROOT)}")

    return 1 if has_blocking_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
