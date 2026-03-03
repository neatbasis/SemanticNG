from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = ROOT / ".github" / "scripts" / "run_promotion_checks.sh"


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)

    script_path = repo / ".github" / "scripts" / "run_promotion_checks.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_SCRIPT, script_path)
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

    # Minimal files expected by the hook paths.
    _write_file(repo / "docs" / "doc_freshness_slo.json", "{}\n")
    _write_file(repo / ".github" / "pull_request_template.md", "template\n")
    _write_file(repo / "docs" / "dod_manifest.json", "{}\n")

    validator_names = [
        "validate_milestone_docs.py",
        "validate_governance_sync.py",
        "validate_governance_docs_schema.py",
        "validate_sprint_handoff.py",
        "validate_doc_freshness_slo.py",
        "render_transition_evidence.py",
    ]

    for name in validator_names:
        _write_file(
            repo / ".github" / "scripts" / name,
            """#!/usr/bin/env python3
import os
import pathlib
import sys

fail_target = os.environ.get(\"PROMOTION_TEST_FAIL\")
if fail_target and fail_target == pathlib.Path(__file__).name:
    print(\"forced failure\", file=sys.stderr)
    raise SystemExit(1)
print(\"ok\")
""",
        )

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True, text=True)

    return repo


def _run_hook(repo: Path, *, fail_target: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if fail_target:
        env["PROMOTION_TEST_FAIL"] = fail_target
    return subprocess.run(
        ["bash", ".github/scripts/run_promotion_checks.sh"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def test_unrelated_staged_change_skips_promotion_checks(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _write_file(repo / "src" / "feature.py", "print('hello')\n")
    subprocess.run(["git", "add", "src/feature.py"], cwd=repo, check=True)

    result = _run_hook(repo)

    assert result.returncode == 0
    assert "Promotion checks skipped" in result.stdout


def test_relevant_staged_policy_violation_blocks_commit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _write_file(repo / "docs" / "milestones" / "m1.md", "# milestone\n")
    subprocess.run(["git", "add", "docs/milestones/m1.md"], cwd=repo, check=True)

    result = _run_hook(repo, fail_target="validate_governance_sync.py")

    assert result.returncode != 0
    assert "COMMIT BLOCKED" in result.stdout
    assert "Check triggered because" in result.stdout
    assert "python .github/scripts/validate_governance_sync.py" in result.stdout


def test_relevant_clean_change_passes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _write_file(repo / "docs" / "milestones" / "m2.md", "# milestone clean\n")
    subprocess.run(["git", "add", "docs/milestones/m2.md"], cwd=repo, check=True)

    result = _run_hook(repo)

    assert result.returncode == 0
    assert "Promotion checks passed." in result.stdout


def test_semantic_boundary_change_without_contract_docs_blocks_commit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _write_file(repo / "src" / "semanticng" / "interfaces.py", "X = 1\n")
    subprocess.run(["git", "add", "src/semanticng/interfaces.py"], cwd=repo, check=True)

    result = _run_hook(repo)

    assert result.returncode != 0
    assert "semantic boundary contract updates are required" in result.stdout
    assert "src/semanticng/interfaces.py" in result.stdout


def test_semantic_boundary_change_with_contract_docs_passes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _write_file(repo / "src" / "semanticng" / "interfaces.py", "X = 1\n")
    _write_file(repo / "docs" / "system_contract_map.md", "# contract update\n")
    subprocess.run(
        ["git", "add", "src/semanticng/interfaces.py", "docs/system_contract_map.md"],
        cwd=repo,
        check=True,
    )

    result = _run_hook(repo)

    assert result.returncode == 0
    assert "Promotion checks passed." in result.stdout
