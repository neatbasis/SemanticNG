from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "validate_no_regression_budget_update.py"

_spec = importlib.util.spec_from_file_location("validate_no_regression_budget_update", SCRIPT_PATH)
assert _spec and _spec.loader
validate_no_regression_budget_update = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_no_regression_budget_update)


def _policy(baseline: dict[str, int], allowed: dict[str, int]) -> dict:
    return {
        "quality_metric_budget": {
            "baseline": baseline,
            "allowed_regression": allowed,
        }
    }


def test_changed_metrics_detects_diff() -> None:
    changed = validate_no_regression_budget_update._changed_metrics(
        {"ruff_violations": 1, "mypy_errors": 2, "failing_tests": 3},
        {"ruff_violations": 1, "mypy_errors": 4, "failing_tests": 3},
    )

    assert changed == {"mypy_errors": (2, 4)}


def test_metadata_mismatches_requires_remediation_when_baseline_increases() -> None:
    metadata = {
        "status": "approved",
        "checklist": {
            "before_counts": {"ruff_violations": 14},
            "after_counts": {"ruff_violations": 16},
            "justification": "toolchain upgrade",
            "remediation_issue_or_pr": "",
        },
        "timeboxed_exception": {"enabled": False},
    }

    mismatches = validate_no_regression_budget_update._metadata_mismatches(
        metadata,
        baseline_changes={"ruff_violations": (14, 16)},
        allowed_changes={},
    )

    assert (
        "metadata.checklist.remediation_issue_or_pr is required when any baseline count increases."
        in mismatches
    )


def test_metadata_mismatches_requires_timebox_fields_for_nonzero_allowed_regression() -> None:
    metadata = {
        "status": "approved",
        "checklist": {
            "before_counts": {"mypy_errors": 10},
            "after_counts": {"mypy_errors": 10},
            "justification": "temporary compatibility window",
            "remediation_issue_or_pr": "https://example.invalid/issues/1",
        },
        "timeboxed_exception": {"enabled": False},
    }

    mismatches = validate_no_regression_budget_update._metadata_mismatches(
        metadata,
        baseline_changes={},
        allowed_changes={"mypy_errors": (0, 1)},
    )

    assert any("timeboxed_exception.enabled" in mismatch for mismatch in mismatches)
    assert any("approved_by" in mismatch for mismatch in mismatches)


def test_metadata_mismatches_accepts_complete_payload() -> None:
    metadata = {
        "status": "approved",
        "checklist": {
            "before_counts": {"ruff_violations": 14},
            "after_counts": {"ruff_violations": 12},
            "justification": "major toolchain upgrade",
            "remediation_issue_or_pr": "not_applicable",
        },
        "timeboxed_exception": {
            "enabled": True,
            "approved_by": "@quality-gates",
            "approval_expires_on": "2099-01-01",
            "approval_reference": "https://example.invalid/pr/2",
            "rollback_issue_or_pr": "https://example.invalid/issues/2",
        },
    }

    mismatches = validate_no_regression_budget_update._metadata_mismatches(
        metadata,
        baseline_changes={"ruff_violations": (14, 12)},
        allowed_changes={"mypy_errors": (0, 1)},
    )

    assert mismatches == []
