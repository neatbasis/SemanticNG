from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts/ci/run_stage_checks.py"
SPEC = importlib.util.spec_from_file_location("run_stage_checks", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_stage_definitions_include_expected_timeout_budgets() -> None:
    assert MODULE.STAGES["qa-commit"][0].timeout_seconds == 20
    assert MODULE.STAGES["qa-commit"][1].timeout_seconds == 40

    assert MODULE.STAGES["qa-push"][-1].timeout_seconds == 80
    assert MODULE.STAGES["qa-ci"][-1].timeout_seconds == 240


def test_failure_file_extraction_is_deterministic() -> None:
    output = """src/core/engine.py:12: error: boom\ntests/test_invariants.py:9: error: fail\nsrc/core/engine.py:20: error: duplicate\n"""

    assert MODULE._first_failing_files(output) == ["src/core/engine.py", "tests/test_invariants.py"]
