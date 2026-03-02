from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "check_no_regression_budget.py"

_spec = importlib.util.spec_from_file_location("check_no_regression_budget", SCRIPT_PATH)
assert _spec and _spec.loader
check_no_regression_budget = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_no_regression_budget)


def test_parse_ruff_violations_handles_found_summary() -> None:
    output = "Found 14 errors.\n[*] 12 fixable"
    assert check_no_regression_budget._parse_ruff_violations(output) == 14


def test_parse_mypy_errors_handles_found_summary() -> None:
    output = "Found 62 errors in 21 files (checked 76 source files)"
    assert check_no_regression_budget._parse_mypy_errors(output) == 62


def test_parse_failing_tests_extracts_pytest_summary() -> None:
    output = "3 failed, 342 passed, 6 skipped in 2.00s"
    assert check_no_regression_budget._parse_failing_tests(output) == 3


def test_policy_includes_quality_metric_budget_surface() -> None:
    policy_text = (ROOT / "docs" / "no_regression_budget.json").read_text(encoding="utf-8")

    assert '"quality_metric_budget"' in policy_text
    assert '"ruff_violations"' in policy_text
    assert '"mypy_errors"' in policy_text
    assert '"failing_tests"' in policy_text
