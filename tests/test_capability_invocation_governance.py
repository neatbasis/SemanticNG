from __future__ import annotations

from pathlib import Path

from state_renormalization.adapters.persistence import read_jsonl
from state_renormalization.contracts import (
    EvidenceRef,
    HaltRecord,
    PredictionRecord,
    ProjectionState,
)
from state_renormalization.engine import (
    _capability_invocation_policy_decision,
    _persist_policy_denial,
    append_prediction_record,
)


def _prediction(prediction_id: str, scope_key: str) -> PredictionRecord:
    return PredictionRecord(
        prediction_id=prediction_id,
        prediction_key=scope_key,
        scope_key=scope_key,
        filtration_id="filt:test",
        target_variable="user_response_present",
        target_horizon_iso="2026-02-13T00:00:00+00:00",
        issued_at_iso="2026-02-13T00:00:00+00:00",
        assumptions=["prediction_availability.v1"],
        evidence_refs=[EvidenceRef(kind="jsonl", ref="predictions.jsonl@1")],
    )


def test_capability_invocation_allows_side_effect_after_policy_checks(
    make_episode, make_observer
) -> None:
    pred = _prediction("pred:allow", "scope:allow")
    projection = ProjectionState(
        current_predictions={pred.scope_key: pred}, updated_at_iso="2026-02-13T00:00:00+00:00"
    )
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
    assert len(rows) == 2
    assert rows[0]["event_kind"] == "prediction"
    assert rows[1]["event_kind"] == "prediction_record"
    assert rows[1]["prediction_id"] == pred.prediction_id
    evidence_refs = rows[1].get("evidence_refs", [])
    assert any(ref.get("ref") == "test-capability-allow.jsonl@1" for ref in evidence_refs)
    assert not halt_path.exists()


def test_capability_invocation_denial_persists_explainable_halt_and_skips_side_effect(
    make_episode,
) -> None:
    pred = _prediction("pred:deny", "scope:deny")
    projection = ProjectionState(
        current_predictions={pred.scope_key: pred}, updated_at_iso="2026-02-13T00:00:00+00:00"
    )
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


def test_capability_invocation_denial_requires_current_prediction_context(
    make_episode,
) -> None:
    ep = make_episode()
    projection = ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")

    log_path = Path("artifacts/test-capability-current-prediction-required.jsonl")
    halt_path = Path("artifacts/test-capability-current-prediction-required-halts.jsonl")
    for p in (log_path, halt_path):
        if p.exists():
            p.unlink()

    policy_decision = _capability_invocation_policy_decision(
        observer=ep.observer,
        projection_state=projection,
        scope_key="scope:missing",
        prediction_key="scope:missing",
        explicit_gate_pass_present=True,
        action="append_prediction_record_event",
        capability="prediction.persistence",
        required_capability="baseline.invariant_evaluation",
        stage="capability-invocation",
    )
    assert not policy_decision.allowed
    assert policy_decision.denial_code is not None
    assert policy_decision.denial_code.value == "current_prediction_required"

    result = _persist_policy_denial(ep=ep, decision=policy_decision, halt_log_path=halt_path)

    assert isinstance(result, HaltRecord)
    assert result.invariant_id == "capability.invocation.policy.v1"
    assert result.details["policy_code"] == "current_prediction_required"
    assert not log_path.exists()

    halt_rows = list(read_jsonl(halt_path))
    assert len(halt_rows) == 1
    meta, persisted = halt_rows[0]
    assert persisted["invariant_id"] == "capability.invocation.policy.v1"
    assert persisted["details"]["policy_code"] == "current_prediction_required"
    assert persisted["details"]["attempt"]["current_prediction_available"] is False
    assert persisted["evidence"] == [
        {"kind": "capability", "ref": "prediction.persistence"},
        {"kind": "action", "ref": "append_prediction_record_event"},
        {"kind": "policy_code", "ref": "current_prediction_required"},
    ]

    expected_ref = {"kind": "jsonl", "ref": f"{halt_path.name}@{meta['lineno']}"}
    denial_artifact = next(a for a in ep.artifacts if a.get("artifact_kind") == "capability_policy_denial")
    halt_observation = next(a for a in ep.artifacts if a.get("artifact_kind") == "halt_observation")
    assert denial_artifact["halt_evidence_ref"] == expected_ref
    assert halt_observation["halt_evidence_ref"] == expected_ref
