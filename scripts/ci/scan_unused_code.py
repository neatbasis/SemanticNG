#!/usr/bin/env python3
"""Deterministically scan unused-code signals and emit CI artifacts."""

from __future__ import annotations

import json
import re
import subprocess
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
    Surface(name="github_scripts", path=".github/scripts", blocking=False),
    Surface(name="ci_scripts", path="scripts/ci", blocking=False),
    Surface(name="dev_scripts", path="scripts/dev", blocking=False),
)

INLINE_WORKFLOW_RUN_PATTERN = re.compile(r"^\s*(?:-|)\s*run:\s+", re.MULTILINE)


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


def _list_surface_files(surface: Surface) -> list[Path]:
    surface_root = ROOT / surface.path
    if not surface_root.exists():
        return []
    return sorted(file for file in surface_root.rglob("*") if file.is_file())


def _has_inline_shell_workflow_steps(file_path: Path) -> bool:
    if file_path.suffix not in {".yml", ".yaml"}:
        return False
    text = file_path.read_text(encoding="utf-8")
    return bool(INLINE_WORKFLOW_RUN_PATTERN.search(text))


def _surface_coverage(surface: Surface) -> tuple[int, int, str, list[dict[str, object]]]:
    files = _list_surface_files(surface)
    total_file_count = len(files)

    analyzable_files = [file for file in files if file.suffix in {".py", ".pyi"}]
    analyzable_file_count = len(analyzable_files)

    shell_files = [str(file.relative_to(ROOT)) for file in files if file.suffix == ".sh"]
    workflow_files_with_inline_shell = [
        str(file.relative_to(ROOT))
        for file in files
        if _has_inline_shell_workflow_steps(file)
    ]

    unsupported_surface_reasons: list[dict[str, object]] = []
    if shell_files:
        unsupported_surface_reasons.append(
            {
                "kind": "shell_script",
                "reason": "Shell scripts (*.sh) are not analyzed for unused code in this scanner.",
                "files": shell_files,
            }
        )
    if workflow_files_with_inline_shell:
        unsupported_surface_reasons.append(
            {
                "kind": "workflow_inline_shell",
                "reason": "Inline shell in workflow files is not analyzed for unused code in this scanner.",
                "files": workflow_files_with_inline_shell,
            }
        )

    if analyzable_file_count == 0:
        coverage_status = "not_supported" if total_file_count else "covered"
    elif analyzable_file_count < total_file_count:
        coverage_status = "partial"
    else:
        coverage_status = "covered"

    return analyzable_file_count, total_file_count, coverage_status, unsupported_surface_reasons


def main() -> int:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    has_blocking_findings = False
    summary: list[dict[str, object]] = []

    for surface in SURFACES:
        diagnostics, command_text = _run_ruff(surface)
        analyzable_file_count, total_file_count, coverage_status, unsupported_surface_reasons = _surface_coverage(surface)
        scanner = "ruff" if analyzable_file_count else "n/a-shell"
        payload = {
            "surface": surface.name,
            "path": surface.path,
            "blocking": surface.blocking,
            "scanner": scanner,
            "coverage_status": coverage_status,
            "analyzable_file_count": analyzable_file_count,
            "total_file_count": total_file_count,
            "unsupported_surface_reasons": unsupported_surface_reasons,
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
                "scanner": scanner,
                "coverage_status": coverage_status,
                "analyzable_file_count": analyzable_file_count,
                "total_file_count": total_file_count,
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
