from __future__ import annotations

import importlib.util
import json
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


def test_metric_from_output_marks_ruff_ambiguity_unparseable() -> None:
    result = check_no_regression_budget._metric_from_output(
        "ruff_violations", "ruff completed with status detail unavailable"
    )
    assert result["parsed_ok"] is False
    assert result["value"] == 0
    assert "Unable to parse Ruff output" in result["reason"]


def test_metric_from_output_marks_mypy_ambiguity_unparseable() -> None:
    result = check_no_regression_budget._metric_from_output(
        "mypy_errors", "mypy emitted diagnostics in unknown format"
    )
    assert result["parsed_ok"] is False
    assert result["value"] == 0
    assert "Unable to parse mypy output" in result["reason"]


def test_metric_from_output_marks_pytest_ambiguity_unparseable() -> None:
    result = check_no_regression_budget._metric_from_output(
        "failing_tests", "pytest run summary unavailable"
    )
    assert result["parsed_ok"] is False
    assert result["value"] == 0
    assert "Unable to parse pytest output" in result["reason"]


def test_main_fails_closed_on_unparseable_metric_output(tmp_path, monkeypatch, capsys) -> None:
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "quality_metric_budget": {
                    "commands": {
                        "ruff_violations": "ruff-command",
                        "mypy_errors": "mypy-command",
                        "failing_tests": "pytest-command",
                    },
                    "baseline": {
                        "ruff_violations": 0,
                        "mypy_errors": 0,
                        "failing_tests": 0,
                    },
                    "allowed_regression": {
                        "ruff_violations": 0,
                        "mypy_errors": 0,
                        "failing_tests": 0,
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    def fake_run(command: str) -> tuple[int, str]:
        if command == "ruff-command":
            return 0, "nonsensical ruff output"
        if command == "mypy-command":
            return 0, "Success: no issues found in 10 source files"
        return 0, "100 passed in 2.00s"

    monkeypatch.setattr(check_no_regression_budget, "POLICY_PATH", policy_path)
    monkeypatch.setattr(check_no_regression_budget, "_run", fake_run)

    exit_code = check_no_regression_budget.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Metric 'ruff_violations' output was unparseable" in captured.out
    assert "Check command 'ruff-command' and parser expectations." in captured.out


def test_policy_includes_quality_metric_budget_surface() -> None:
    policy_text = (ROOT / "docs" / "no_regression_budget.json").read_text(encoding="utf-8")

    assert '"quality_metric_budget"' in policy_text
    assert '"ruff_violations"' in policy_text
    assert '"mypy_errors"' in policy_text
    assert '"failing_tests"' in policy_text
