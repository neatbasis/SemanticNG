from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "docs" / "toolchain_parity_policy.json"


def _load_policy() -> dict[str, object]:
    return cast(dict[str, object], json.loads(POLICY_PATH.read_text(encoding="utf-8")))


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
    policy = _load_policy()
    workflow = ROOT / ".github" / "workflows" / "toolchain-parity-weekly.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "schedule:" in text
    assert "pre-commit clean" in text
    quality_guardrails = (ROOT / ".github" / "workflows" / "quality-guardrails.yml").read_text(
        encoding="utf-8"
    )
    canonical_targets = cast(list[str], policy["canonical_make_targets"])
    for target in canonical_targets:
        assert target in quality_guardrails


def test_docs_include_generated_parity_policy_block() -> None:
    policy = _load_policy()
    parity_docs = cast(list[str], policy["parity_docs"])
    for doc in parity_docs:
        text = (ROOT / doc).read_text(encoding="utf-8")
        assert "<!-- PARITY_POLICY:START -->" in text
        assert "<!-- PARITY_POLICY:END -->" in text
        python_version = cast(Any, policy["python_version"])
        assert f"- Python baseline: `{python_version}`" in text


def test_makefile_qa_ci_target_runs_stage_runner() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "qa-ci:" in makefile
    assert "\tpython scripts/ci/run_stage_checks.py qa-ci" in makefile
    assert "qa-ci-equivalent:" in makefile
    assert "\t$(MAKE) qa-ci" in makefile


def test_makefile_qa_local_remains_fast_dev_flow() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "qa-local: verify-dev-setup qa-push qa-test-cov qa-full-type-surface" in makefile
    assert "bootstrap: setup-dev" in makefile
    assert "verify-dev-setup: bootstrap-preflight verify-precommit-installed" in makefile


def test_state_renorm_milestone_baseline_uses_canonical_make_targets() -> None:
    workflow = (ROOT / ".github" / "workflows" / "state-renorm-milestone-gate.yml").read_text(
        encoding="utf-8"
    )

    assert "run: make qa-hook-parity" in workflow
    assert "run: make qa-test-cov" in workflow
    assert "pytest --cov --cov-report=term-missing --cov-report=xml" not in workflow


def test_local_quality_hooks_use_python_language_with_project_test_extra() -> None:
    precommit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    for hook_id in ("qa-commit-stage", "qa-push-stage", "precommit-governance-selector"):
        start = precommit.index(f"- id: {hook_id}")
        end = precommit.find("\n      - id:", start + 1)
        block = precommit[start:] if end == -1 else precommit[start:end]
        assert "language: python" in block
        assert "additional_dependencies:" in block
        assert "- .[test]" in block


def test_system_hook_runtime_assumptions_are_documented() -> None:
    precommit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "dev_toolchain_parity.md").read_text(encoding="utf-8")

    start = precommit.index("- id: promotion-governance-pokayoke")
    end = precommit.find("\n      - id:", start + 1)
    block = precommit[start:] if end == -1 else precommit[start:end]

    assert "language: system" in block
    for required_tool in ("bash", "git", "python"):
        assert f"- `{required_tool}`" in docs


def test_check_toolchain_parity_script_passes_for_repo_state() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ci/check_toolchain_parity.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
