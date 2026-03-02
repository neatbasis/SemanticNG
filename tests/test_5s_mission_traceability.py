from __future__ import annotations

import subprocess
from pathlib import Path


def test_validate_5s_mission_traceability_script_passes() -> None:
    result = subprocess.run(
        ["python", "scripts/ci/validate_5s_mission_traceability.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "validation passed" in result.stdout


def test_traceability_matrix_exists_with_expected_header() -> None:
    text = Path("docs/5s_mission_traceability.md").read_text(encoding="utf-8")
    assert "| 5S principle | Mission principle(s) | Governing axioms/invariants |" in text
