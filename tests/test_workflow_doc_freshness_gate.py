from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_GATE_WORKFLOW = ROOT / ".github" / "workflows" / "state-renorm-milestone-gate.yml"
QUALITY_GUARDRAILS_WORKFLOW = ROOT / ".github" / "workflows" / "quality-guardrails.yml"
FRESHNESS_COMMAND = "python .github/scripts/validate_doc_freshness_slo.py --config docs/doc_freshness_slo.json"


def test_state_gate_has_doc_freshness_command_step() -> None:
    content = STATE_GATE_WORKFLOW.read_text(encoding="utf-8")

    assert "- name: Validate documentation freshness SLO" in content
    assert FRESHNESS_COMMAND in content


def test_state_gate_path_filters_include_doc_freshness_controls() -> None:
    content = STATE_GATE_WORKFLOW.read_text(encoding="utf-8")

    assert content.count("- '.github/scripts/validate_doc_freshness_slo.py'") == 3
    assert content.count("- 'docs/doc_freshness_slo.json'") == 3


def test_quality_guardrails_runs_doc_freshness_validator() -> None:
    content = QUALITY_GUARDRAILS_WORKFLOW.read_text(encoding="utf-8")

    assert "- name: Validate documentation freshness SLO" in content
    assert FRESHNESS_COMMAND in content
