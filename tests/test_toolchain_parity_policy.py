from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_precommit_parity_policy_passes_for_repo_state() -> None:
    result = subprocess.run(
        [sys.executable, ".github/scripts/check_precommit_parity.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_weekly_toolchain_parity_workflow_exists_and_is_scheduled() -> None:
    workflow = ROOT / ".github" / "workflows" / "toolchain-parity-weekly.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "schedule:" in text
    assert "pre-commit clean" in text
    assert "mypy --config-file=pyproject.toml src tests" in text
