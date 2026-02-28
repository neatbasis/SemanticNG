from __future__ import annotations

from pathlib import Path

from state_renormalization.contracts import HaltRecord, PredictionRecord, ProjectionState
from state_renormalization.adapters.persistence import read_jsonl
from state_renormalization.engine import append_prediction_record


def _prediction(prediction_id: str, scope_key: str) -> PredictionRecord:
    return PredictionRecord(
        prediction_id=prediction_id,
        prediction_key=scope_key,
        scope_key=scope_key,
        filtration_ref="filt:test",
        variable="user_response_present",
        horizon_iso="2026-02-13T00:00:00+00:00",
        issued_at_iso="2026-02-13T00:00:00+00:00",
        invariants_assumed=["prediction_availability.v1"],
        evidence_links=[{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
    )


def test_capability_invocation_allows_side_effect_after_policy_checks(make_episode, make_observer) -> None:
    pred = _prediction("pred:allow", "scope:allow")
    projection = ProjectionState(current_predictions={pred.scope_key: pred}, updated_at_iso="2026-02-13T00:00:00+00:00")
    ep = make_episode(observer=make_observer(capabilities=["baseline.invariant_evaluation"]))

    log_path = Path("artifacts/test-capability-allow.jsonl")
    halt_path = Path("artifacts/test-capability-allow-halts.jsonl")
    for p in (log_path, halt_path):
        if p.exists():
            p.unlink()

    result = append_prediction_record(
        pred,
        prediction_log_path=log_path,
        halt_log_path=halt_path,
        projection_state=projection,
        explicit_gate_pass_present=True,
        episode=ep,
    )

    assert isinstance(result, dict)
    rows = [row for _, row in read_jsonl(log_path)]
    assert len(rows) == 1
    assert rows[0]["prediction_id"] == pred.prediction_id
    assert not halt_path.exists()


def test_capability_invocation_denial_persists_explainable_halt_and_skips_side_effect(make_episode) -> None:
    pred = _prediction("pred:deny", "scope:deny")
    projection = ProjectionState(current_predictions={pred.scope_key: pred}, updated_at_iso="2026-02-13T00:00:00+00:00")
    ep = make_episode()

    log_path = Path("artifacts/test-capability-deny.jsonl")
    halt_path = Path("artifacts/test-capability-deny-halts.jsonl")
    for p in (log_path, halt_path):
        if p.exists():
            p.unlink()

    result = append_prediction_record(
        pred,
        prediction_log_path=log_path,
        halt_log_path=halt_path,
        projection_state=projection,
        explicit_gate_pass_present=False,
        episode=ep,
    )

    assert isinstance(result, HaltRecord)
    assert result.invariant_id == "capability.invocation.policy.v1"
    assert result.details["policy_code"] == "explicit_gate_pass_required"
    assert not log_path.exists()

    halt_rows = [row for _, row in read_jsonl(halt_path)]
    assert len(halt_rows) == 1
    assert halt_rows[0]["invariant_id"] == "capability.invocation.policy.v1"
