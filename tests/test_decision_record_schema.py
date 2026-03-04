from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "ci" / "validate_decision_records.py"
FIXTURES = ROOT / "tests" / "fixtures" / "decision_records"

spec = importlib.util.spec_from_file_location("validate_decision_records", MODULE_PATH)
assert spec and spec.loader
validate_decision_records = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validate_decision_records
spec.loader.exec_module(validate_decision_records)


def test_valid_fixtures_pass() -> None:
    errors = validate_decision_records.validate_decision_records(FIXTURES / "valid")

    assert errors == []


def test_missing_canonical_references_fail() -> None:
    errors = validate_decision_records.validate_decision_records(FIXTURES / "invalid_missing_ref")

    assert any("canonical_refs missing required reference" in error for error in errors)


def test_duplicate_id_fails() -> None:
    errors = validate_decision_records.validate_decision_records(FIXTURES / "invalid_duplicate_id")

    assert any("duplicate id" in error for error in errors)


def test_non_monotonic_date_ordering_fails() -> None:
    errors = validate_decision_records.validate_decision_records(FIXTURES / "invalid_non_monotonic")

    assert any("non-monotonic date ordering" in error for error in errors)
