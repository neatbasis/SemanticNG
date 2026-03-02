from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "docs" / "toolchain_parity_policy.json"


def _load_policy() -> dict[str, object]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


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
    for target in policy["canonical_make_targets"]:
        assert target in quality_guardrails


def test_docs_include_generated_parity_policy_block() -> None:
    policy = _load_policy()
    for doc in policy["parity_docs"]:
        text = (ROOT / doc).read_text(encoding="utf-8")
        assert "<!-- PARITY_POLICY:START -->" in text
        assert "<!-- PARITY_POLICY:END -->" in text
        assert f"- Python baseline: `{policy['python_version']}`" in text


def test_makefile_qa_ci_equivalent_target_runs_canonical_sequence() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "qa-ci-equivalent:" in makefile
    assert "	python .github/scripts/check_no_regression_budget.py" in makefile
    assert "	$(MAKE) qa-hook-parity" in makefile
    assert "	$(MAKE) qa-test-cov" in makefile
    assert "	$(MAKE) qa-full-type-surface" in makefile


def test_makefile_qa_local_remains_fast_dev_flow() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "qa-local: bootstrap qa-hook-parity qa-test-cov qa-full-type-surface" in makefile


def test_state_renorm_milestone_baseline_uses_canonical_make_targets() -> None:
    workflow = (ROOT / ".github" / "workflows" / "state-renorm-milestone-gate.yml").read_text(
        encoding="utf-8"
    )

    assert "run: make qa-hook-parity" in workflow
    assert "run: make qa-test-cov" in workflow
    assert "pytest --cov --cov-report=term-missing --cov-report=xml" not in workflow
