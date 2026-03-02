from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / ".github/scripts/classify_precommit_failures.py"
SPEC = importlib.util.spec_from_file_location("classify_precommit_failures", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_taxonomy_keys_are_stable() -> None:
    assert MODULE.TAXONOMY_KEYS == ("ruff", "mypy", "pytest", "autofix_drift", "infra_setup")


def test_output_schema_is_stable() -> None:
    result = MODULE.classify("src/state_renormalization/engine.py:12: F401\nerror: Incompatible types [arg-type]")

    assert set(result.keys()) == {
        "schema_version",
        "taxonomy",
        "classes_detected",
        "signals",
        "touched_paths",
    }
    assert result["taxonomy"] == list(MODULE.TAXONOMY_KEYS)
    assert set(result["signals"].keys()) == {
        "auto_fix_required",
        "missing_dependency",
        "ruff_codes",
        "mypy_codes",
        "pytest_failure_detected",
    }


def test_autofix_drift_classified_separately_from_infra_setup() -> None:
    result = MODULE.classify("ruff.................................................Failed\n- files were modified by this hook")

    assert "autofix_drift" in result["classes_detected"]
    assert "infra_setup" not in result["classes_detected"]


def test_missing_dependency_remains_in_infra_setup() -> None:
    result = MODULE.classify("error: Cannot find implementation or library stub for module named x [import-not-found]")

    assert "infra_setup" in result["classes_detected"]
    assert "autofix_drift" not in result["classes_detected"]
