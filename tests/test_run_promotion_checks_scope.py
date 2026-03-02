from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "run_promotion_checks.sh"
PROBE = ROOT / "tests" / "promotion_scope_probe.txt"
DOC_PROBE = ROOT / "docs" / "promotion_scope_probe.md"


def _run_script() -> subprocess.CompletedProcess[str]:
    env = {
        "PROMOTION_CHECK_SCOPE": "staged",
        "PROMOTION_CHECK_DRY_RUN": "1",
    }
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, **env},
    )


def _clear_probe() -> None:
    subprocess.run(["git", "reset", "--", str(PROBE)], cwd=ROOT, check=False)
    if PROBE.exists():
        PROBE.unlink()


def test_promotion_checks_skip_when_no_staged_files() -> None:
    _clear_probe()
    result = _run_script()

    assert result.returncode == 0
    assert "No staged files; skipping promotion checks." in result.stdout


def test_promotion_checks_skip_non_policy_staged_files() -> None:
    PROBE.parent.mkdir(parents=True, exist_ok=True)
    PROBE.write_text("probe\n", encoding="utf-8")
    subprocess.run(["git", "add", str(PROBE)], cwd=ROOT, check=True)

    try:
        result = _run_script()
    finally:
        _clear_probe()

    assert result.returncode == 0
    assert "No staged promotion-policy files detected" in result.stdout
    assert "dry-run scope=doc-freshness-slo" not in result.stdout


def test_promotion_checks_select_relevant_scope_for_docs_changes() -> None:
    DOC_PROBE.write_text("probe\n", encoding="utf-8")
    subprocess.run(["git", "add", str(DOC_PROBE)], cwd=ROOT, check=True)

    try:
        result = _run_script()
    finally:
        subprocess.run(["git", "reset", "--", str(DOC_PROBE)], cwd=ROOT, check=False)
        if DOC_PROBE.exists():
            DOC_PROBE.unlink()

    assert result.returncode == 0
    assert "dry-run scope=doc-freshness-slo" in result.stdout
