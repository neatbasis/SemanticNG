from __future__ import annotations

from pathlib import Path

from scripts.ci import validate_workflow_topology

MARKER = validate_workflow_topology.REQUIRED_ORCHESTRATOR_MARKER


def _write_workflow(path: Path, name: str, *, orchestrator: bool = False) -> None:
    marker_line = f"\n{MARKER}\n" if orchestrator else "\n"
    path.write_text(
        f"name: {name}{marker_line}on:\n  workflow_dispatch:\n\njobs:\n  noop:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )


def test_valid_single_orchestrator_fixture_set(tmp_path: Path) -> None:
    _write_workflow(tmp_path / "quality-guardrails.yml", "Quality Guardrails", orchestrator=True)
    _write_workflow(tmp_path / "weekly-audit.yml", "Weekly Audit")

    issues = validate_workflow_topology.validate_workflow_topology(tmp_path)

    assert issues == []


def test_invalid_multi_orchestrator_fixture_set(tmp_path: Path) -> None:
    _write_workflow(tmp_path / "quality-guardrails.yml", "Quality Guardrails", orchestrator=True)
    _write_workflow(tmp_path / "milestone-gate.yml", "Milestone Gate", orchestrator=True)

    issues = validate_workflow_topology.validate_workflow_topology(tmp_path)

    assert issues
    assert "expected exactly one required orchestrator workflow" in issues[0]
    assert "found 2" in issues[0]
