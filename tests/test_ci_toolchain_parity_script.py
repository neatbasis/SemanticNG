from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_toolchain_parity_script_passes_for_repo_state() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ci/check_toolchain_parity.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
