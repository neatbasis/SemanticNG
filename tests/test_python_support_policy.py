from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_support_policy_script_passes_for_repo_state() -> None:
    result = subprocess.run(
        [sys.executable, ".github/scripts/check_python_support_policy.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
