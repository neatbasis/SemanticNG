from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

POLICY_PATH = Path("docs/no_regression_budget.json")


class ParseResult(TypedDict):
    value: int
    parsed_ok: bool
    reason: str


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


def main() -> int:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    quality_policy = policy.get("quality_metric_budget")
    if not isinstance(quality_policy, dict):
        print("Missing quality_metric_budget in docs/no_regression_budget.json")
        return 1

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

    if failures:
        print("No-regression budget check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("No-regression budget check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
