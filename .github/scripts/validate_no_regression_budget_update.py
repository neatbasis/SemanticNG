#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from datetime import date
from pathlib import Path

POLICY_PATH = Path("docs/no_regression_budget.json")
METADATA_PATH = Path("docs/no_regression_budget_update_request.json")
METRICS = ("ruff_violations", "mypy_errors", "failing_tests")


def _git_command_failure_message(command: list[str], error: subprocess.CalledProcessError) -> str:
    command_rendered = " ".join(command)
    stderr = (error.stderr or "").strip()
    details = f" Command: `{command_rendered}` exited with status {error.returncode}."
    if stderr:
        details += f" stderr: {stderr}"
    return (
        "Unable to resolve Git revision context for no-regression budget validation."
        f"{details}"
        " This usually indicates a shallow checkout without the required parent commit history."
        " Remediation: set checkout fetch-depth >= 2 (or 0 for full history)"
        " and/or provide BASE_SHA explicitly."
    )


def _run_git(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.PIPE).strip()
    except subprocess.CalledProcessError as error:
        raise RuntimeError(_git_command_failure_message(command, error)) from error


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_policy_at_rev(rev: str) -> dict:
    raw = _run_git(["git", "show", f"{rev}:{POLICY_PATH.as_posix()}"])
    return json.loads(raw)


def _extract_counts(policy: dict, field: str) -> dict[str, int]:
    quality = policy.get("quality_metric_budget", {})
    counts = quality.get(field, {})
    if not isinstance(counts, dict):
        return {}
    return {metric: counts.get(metric) for metric in METRICS}


def _changed_metrics(base: dict[str, int], head: dict[str, int]) -> dict[str, tuple[int, int]]:
    changed: dict[str, tuple[int, int]] = {}
    for metric in METRICS:
        before = base.get(metric)
        after = head.get(metric)
        if before != after:
            changed[metric] = (before, after)
    return changed


def _require_nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _metadata_mismatches(metadata: dict, baseline_changes: dict, allowed_changes: dict) -> list[str]:
    mismatches: list[str] = []

    if metadata.get("status") != "approved":
        mismatches.append("metadata.status must be 'approved' when baseline/allowed values change.")

    checklist = metadata.get("checklist")
    if not isinstance(checklist, dict):
        return mismatches + ["metadata.checklist must be an object."]

    before_counts = checklist.get("before_counts")
    after_counts = checklist.get("after_counts")
    if not isinstance(before_counts, dict) or not isinstance(after_counts, dict):
        mismatches.append("metadata.checklist.before_counts and after_counts must be objects.")
    else:
        for metric in METRICS:
            if metric in baseline_changes:
                before, after = baseline_changes[metric]
                if before_counts.get(metric) != before:
                    mismatches.append(
                        f"metadata.checklist.before_counts.{metric} must equal baseline pre-change value {before}."
                    )
                if after_counts.get(metric) != after:
                    mismatches.append(
                        f"metadata.checklist.after_counts.{metric} must equal baseline post-change value {after}."
                    )

    if not _require_nonempty_str(checklist.get("justification")):
        mismatches.append("metadata.checklist.justification must be a non-empty string.")

    increased = [metric for metric, (before, after) in baseline_changes.items() if isinstance(before, int) and isinstance(after, int) and after > before]
    remediation = checklist.get("remediation_issue_or_pr")
    if increased and not _require_nonempty_str(remediation):
        mismatches.append(
            "metadata.checklist.remediation_issue_or_pr is required when any baseline count increases."
        )

    allowed_nonzero = [metric for metric, (_, after) in allowed_changes.items() if isinstance(after, int) and after > 0]
    if allowed_nonzero:
        tx = metadata.get("timeboxed_exception")
        if not isinstance(tx, dict):
            return mismatches + ["metadata.timeboxed_exception must be an object when allowed_regression > 0."]

        if tx.get("enabled") is not True:
            mismatches.append("metadata.timeboxed_exception.enabled must be true when allowed_regression > 0.")
        if not _require_nonempty_str(tx.get("approved_by")):
            mismatches.append("metadata.timeboxed_exception.approved_by must be provided when allowed_regression > 0.")
        expiry = tx.get("approval_expires_on")
        if not _require_nonempty_str(expiry):
            mismatches.append(
                "metadata.timeboxed_exception.approval_expires_on must be provided when allowed_regression > 0."
            )
        else:
            try:
                parsed = date.fromisoformat(expiry)
                if parsed <= date.today():
                    mismatches.append("metadata.timeboxed_exception.approval_expires_on must be a future date.")
            except ValueError:
                mismatches.append("metadata.timeboxed_exception.approval_expires_on must use YYYY-MM-DD format.")

        if not _require_nonempty_str(tx.get("approval_reference")):
            mismatches.append(
                "metadata.timeboxed_exception.approval_reference must link to approval evidence when allowed_regression > 0."
            )
        if not _require_nonempty_str(tx.get("rollback_issue_or_pr")):
            mismatches.append(
                "metadata.timeboxed_exception.rollback_issue_or_pr must link to rollback/remediation plan when allowed_regression > 0."
            )

    return mismatches


def main() -> int:
    try:
        head_sha = os.environ.get("HEAD_SHA") or _run_git(["git", "rev-parse", "HEAD"])
        base_sha = os.environ.get("BASE_SHA")
        if not base_sha:
            base_sha = _run_git(["git", "rev-parse", f"{head_sha}~1"])

        head_policy = _load_json(POLICY_PATH)
        base_policy = _load_policy_at_rev(base_sha)
    except RuntimeError as error:
        print(error)
        return 2

    except FileNotFoundError as error:
        print(
            "Unable to execute git while validating no-regression budget updates."
            " Ensure git is available in the runner environment and BASE_SHA is provided explicitly."
            f" Details: {error}"
        )
        return 2

    baseline_changes = _changed_metrics(_extract_counts(base_policy, "baseline"), _extract_counts(head_policy, "baseline"))
    allowed_changes = _changed_metrics(_extract_counts(base_policy, "allowed_regression"), _extract_counts(head_policy, "allowed_regression"))

    if not baseline_changes and not allowed_changes:
        print("No baseline/allowed_regression changes detected.")
        return 0

    if not METADATA_PATH.exists():
        print(
            "Baseline/allowed_regression values changed, but docs/no_regression_budget_update_request.json is missing."
        )
        return 1

    metadata = _load_json(METADATA_PATH)
    mismatches = _metadata_mismatches(metadata, baseline_changes, allowed_changes)
    if mismatches:
        print("No-regression baseline update governance validation failed:")
        for mismatch in mismatches:
            print(f"- {mismatch}")
        return 1

    print("No-regression baseline update governance validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
