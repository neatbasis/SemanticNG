from __future__ import annotations

from pathlib import Path

from state_renormalization.demo_runner import run_packs


def test_run_packs_emits_turn_details_and_summary_metrics() -> None:
    report = run_packs(Path("demos/scenario_packs"))

    sessions = report["sessions"]
    contexts = {session["context"] for session in sessions}
    assert {"scheduling", "safety_critical_instruction", "ontology_schema_alignment"}.issubset(contexts)

    first_turn = sessions[0]["turns"][0]
    assert "prediction_issued" in first_turn
    assert "evidence_used" in first_turn
    assert "intervention_events" in first_turn
    assert "invariant_checks" in first_turn
    assert "halt_issue_warn_outcome" in first_turn
    assert "correction_metric" in first_turn

    summary = report["summary_metrics"]
    assert set(summary) == {
        "invariant_pass_rate",
        "intervention_rate",
        "correction_trend",
        "recovery_success_after_halts",
    }
    assert 0.0 <= summary["invariant_pass_rate"] <= 1.0
    assert 0.0 <= summary["intervention_rate"] <= 1.0
    assert 0.0 <= summary["recovery_success_after_halts"] <= 1.0
