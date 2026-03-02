from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci" / "validate_program_sync.py"


def test_status_sync_check_passes_on_repo_state() -> None:
    result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=False, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Program sync validation passed." in result.stdout
