from __future__ import annotations

import json
import re
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import TypedDict

POLICY_PATH = Path("docs/no_regression_budget.json")
SCRIPT_SURFACE_BASELINE_PATH = Path("docs/process/script_surfaces_unused_code_baseline.json")
SCRIPT_SURFACE_SUMMARY_PATH = Path("artifacts/unused_code/summary.json")


class ParseResult(TypedDict):
    value: int
    parsed_ok: bool
    reason: str


class ScriptSurfaceResult(TypedDict):
    current: int
    threshold: int
    blocking: bool


def _run(command: str) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, output


def _parse_ruff_violations(output: str) -> int:
    if "All checks passed" in output:
        return 0
    match = re.search(r"Found\s+(\d+)\s+error", output)
    return int(match.group(1)) if match else 0


def _parse_mypy_errors(output: str) -> int:
    if "Success: no issues found" in output:
        return 0
    match = re.search(r"Found\s+(\d+)\s+error", output)
    return int(match.group(1)) if match else 0


def _parse_failing_tests(output: str) -> int:
    match = re.search(r"(\d+)\s+failed", output)
    return int(match.group(1)) if match else 0


def _metric_from_output(metric: str, output: str) -> ParseResult:
    if metric == "ruff_violations":
        if "All checks passed" in output:
            return {"value": 0, "parsed_ok": True, "reason": "ruff success summary detected"}
        match = re.search(r"Found\s+(\d+)\s+error", output)
        if match:
            return {
                "value": int(match.group(1)),
                "parsed_ok": True,
                "reason": "ruff error summary detected",
            }
        return {
            "value": 0,
            "parsed_ok": False,
            "reason": "Unable to parse Ruff output. Expected 'All checks passed' or 'Found <N> error(s)'.",
        }
    if metric == "mypy_errors":
        if "Success: no issues found" in output:
            return {"value": 0, "parsed_ok": True, "reason": "mypy success summary detected"}
        match = re.search(r"Found\s+(\d+)\s+error", output)
        if match:
            return {
                "value": int(match.group(1)),
                "parsed_ok": True,
                "reason": "mypy error summary detected",
            }
        return {
            "value": 0,
            "parsed_ok": False,
            "reason": "Unable to parse mypy output. Expected 'Success: no issues found' or 'Found <N> error(s)'.",
        }
    if metric == "failing_tests":
        match = re.search(r"(\d+)\s+failed", output)
        if match:
            return {
                "value": int(match.group(1)),
                "parsed_ok": True,
                "reason": "pytest failing-test summary detected",
            }
        if re.search(r"(\d+)\s+passed", output) or "no tests ran" in output:
            return {"value": 0, "parsed_ok": True, "reason": "pytest non-failure summary detected"}
        return {
            "value": 0,
            "parsed_ok": False,
            "reason": "Unable to parse pytest output. Expected '<N> failed', '<N> passed', or 'no tests ran'.",
        }
    raise ValueError(f"Unsupported metric: {metric}")


def _check_quality_metric_budget() -> list[str]:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    quality_policy = policy.get("quality_metric_budget")
    if not isinstance(quality_policy, dict):
        return ["Missing quality_metric_budget in docs/no_regression_budget.json"]

    commands = quality_policy.get("commands", {})
    baseline = quality_policy.get("baseline", {})
    allowed = quality_policy.get("allowed_regression", {})

    failures: list[str] = []

    for metric in ("ruff_violations", "mypy_errors", "failing_tests"):
        command = commands.get(metric)
        if not isinstance(command, str) or not command.strip():
            failures.append(f"Missing command for metric '{metric}'.")
            continue

        _, output = _run(command)
        parse_result = _metric_from_output(metric, output)
        current = parse_result["value"]

        if not parse_result["parsed_ok"]:
            failures.append(
                f"Metric '{metric}' output was unparseable. {parse_result['reason']} Check command '{command}' and parser expectations."
            )
            continue

        baseline_value = baseline.get(metric)
        allowed_value = allowed.get(metric)
        if not isinstance(baseline_value, int) or not isinstance(allowed_value, int):
            failures.append(f"Metric '{metric}' baseline/allowed values must be integers.")
            continue

        threshold = baseline_value + allowed_value
        print(
            f"{metric}: current={current} baseline={baseline_value} allowed={allowed_value} threshold={threshold}"
        )
        if current > threshold:
            failures.append(
                f"Regression detected for '{metric}': current={current} exceeds threshold={threshold}."
            )

    return failures


def _script_surface_results(
    *,
    baseline_file: Path,
    summary_file: Path,
    enforcement_phase: str,
) -> tuple[list[str], list[str], dict[str, ScriptSurfaceResult]]:
    baseline_payload = json.loads(baseline_file.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_file.read_text(encoding="utf-8"))

    surfaces_config = baseline_payload.get("surfaces")
    if not isinstance(surfaces_config, dict):
        return ["script surface baseline file is missing a 'surfaces' object."], [], {}

    blocking_by_phase = baseline_payload.get("blocking_surfaces_by_phase")
    if not isinstance(blocking_by_phase, dict):
        return ["script surface baseline file is missing 'blocking_surfaces_by_phase'."], [], {}

    blocking_surfaces = blocking_by_phase.get(enforcement_phase)
    if not isinstance(blocking_surfaces, list) or not all(isinstance(item, str) for item in blocking_surfaces):
        return [f"script surface baseline file has invalid blocking set for phase '{enforcement_phase}'."], [], {}

    summary_surfaces = summary_payload.get("surfaces")
    if not isinstance(summary_surfaces, list):
        return ["summary file is missing a 'surfaces' array."], [], {}

    summary_by_name: dict[str, dict[str, object]] = {}
    for entry in summary_surfaces:
        if isinstance(entry, dict) and isinstance(entry.get("surface"), str):
            summary_by_name[str(entry["surface"])] = entry

    failures: list[str] = []
    warnings: list[str] = []
    results: dict[str, ScriptSurfaceResult] = {}

    for surface_name, config in surfaces_config.items():
        if not isinstance(config, dict):
            failures.append(f"Surface '{surface_name}' config must be an object.")
            continue
        baseline_count = config.get("baseline_diagnostic_count")
        allowed_regression = config.get("allowed_regression")
        if not isinstance(baseline_count, int) or not isinstance(allowed_regression, int):
            failures.append(
                f"Surface '{surface_name}' baseline_diagnostic_count and allowed_regression must be integers."
            )
            continue

        summary_entry = summary_by_name.get(surface_name)
        if not isinstance(summary_entry, dict):
            failures.append(f"Surface '{surface_name}' was not found in summary file {summary_file}.")
            continue
        current_count = summary_entry.get("diagnostic_count")
        if not isinstance(current_count, int):
            failures.append(f"Surface '{surface_name}' has non-integer diagnostic_count in summary file.")
            continue

        threshold = baseline_count + allowed_regression
        is_blocking = surface_name in blocking_surfaces
        results[surface_name] = {
            "current": current_count,
            "threshold": threshold,
            "blocking": is_blocking,
        }

        print(
            f"script_surface[{surface_name}] phase={enforcement_phase} current={current_count} "
            f"baseline={baseline_count} allowed={allowed_regression} threshold={threshold} "
            f"blocking={'yes' if is_blocking else 'no'}"
        )

        if current_count > threshold:
            message = (
                f"Script-surface regression for '{surface_name}': current={current_count} "
                f"exceeds threshold={threshold} (phase={enforcement_phase})."
            )
            if is_blocking:
                failures.append(message)
            else:
                warnings.append(message)

    return failures, warnings, results


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run no-regression checks for quality metrics and script surfaces.")
    parser.add_argument(
        "--check-script-surfaces",
        action="store_true",
        help="Compare artifacts/unused_code/summary.json against script surface baseline policy.",
    )
    parser.add_argument(
        "--script-baseline-file",
        type=Path,
        default=SCRIPT_SURFACE_BASELINE_PATH,
        help="Path to script-surface baseline JSON policy.",
    )
    parser.add_argument(
        "--script-summary-file",
        type=Path,
        default=SCRIPT_SURFACE_SUMMARY_PATH,
        help="Path to current scan summary JSON produced by scripts/ci/scan_unused_code.py.",
    )
    parser.add_argument(
        "--script-enforcement-phase",
        choices=("measure-only", "block-ci-scripts", "block-ci-and-github-scripts"),
        default="measure-only",
        help="Blocking profile used for script-surface regression enforcement.",
    )
    parser.add_argument(
        "--skip-quality-metrics",
        action="store_true",
        help="Skip legacy quality_metric_budget checks from docs/no_regression_budget.json.",
    )
    return parser


def main() -> int:
    args, _unknown = _build_parser().parse_known_args()

    failures: list[str] = []
    warnings: list[str] = []

    if not args.skip_quality_metrics:
        failures.extend(_check_quality_metric_budget())

    if args.check_script_surfaces:
        if not args.script_baseline_file.exists():
            failures.append(f"Script baseline file not found: {args.script_baseline_file}")
        elif not args.script_summary_file.exists():
            failures.append(
                f"Script summary file not found: {args.script_summary_file}. Run scripts/ci/scan_unused_code.py first."
            )
        else:
            script_failures, script_warnings, _ = _script_surface_results(
                baseline_file=args.script_baseline_file,
                summary_file=args.script_summary_file,
                enforcement_phase=args.script_enforcement_phase,
            )
            failures.extend(script_failures)
            warnings.extend(script_warnings)

    for warning in warnings:
        print(f"WARNING: {warning}")

    if failures:
        print("No-regression budget check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("No-regression budget check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
