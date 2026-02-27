from __future__ import annotations

from pathlib import Path

from state_renormalization.contracts import PredictionRecord, ProjectionState
from state_renormalization.engine import append_prediction_record, evaluate_invariant_gates, project_current


FIXED_PREDICTION = {
    "prediction_id": "pred:test",
    "scope_key": "room:kitchen:light",
    "filtration_id": "filt:1",
    "variable": "light_on",
    "horizon_iso": "2026-02-13T00:05:00+00:00",
    "distribution_kind": "bernoulli",
    "distribution_params": {"p": 0.7},
    "confidence": 0.88,
    "uncertainty": 0.12,
    "issued_at_iso": "2026-02-13T00:00:00+00:00",
    "valid_until_iso": "2026-02-13T00:10:00+00:00",
    "stopping_time_iso": None,
    "invariants_assumed": ["P0_NO_CURRENT_PREDICTION"],
    "evidence_refs": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
    "conditional_expectation": None,
    "conditional_variance": None,
}


def test_prediction_record_json_round_trip() -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    dumped = pred.model_dump(mode="json")
    reloaded = PredictionRecord.model_validate(dumped)

    assert reloaded == pred


def test_post_write_gate_passes_when_evidence_and_projection_current() -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)

    gate = evaluate_invariant_gates(
        ep=None,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        current_predictions={pred.scope_key: pred.prediction_id},
        prediction_log_available=True,
        just_written_prediction={
            "key": pred.scope_key,
            "evidence_refs": [e.model_dump(mode="json") for e in pred.evidence_refs],
        },
    )

    assert gate.kind == "prediction"
    assert gate.halt is None
    assert gate.post_write
    assert gate.post_write[0].code == "prediction_write_materialized"


def test_post_write_gate_halts_when_append_evidence_missing(tmp_path: Path) -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)

    gate = evaluate_invariant_gates(
        ep=None,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        current_predictions={pred.scope_key: pred.prediction_id},
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": []},
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert gate.kind == "halt"
    assert gate.post_write
    assert gate.post_write[0].code == "prediction_append_unverified"
    assert gate.halt is not None
    assert gate.halt.stage == "post_write"
    assert gate.halt.invariant_id == "P1_WRITE_BEFORE_USE"
    assert gate.halt.reason == "Prediction append did not produce retrievable evidence."
    assert gate.halt.evidence_refs == [{"kind": "scope", "value": pred.scope_key}]
    assert gate.halt.retryable is True


def test_halt_artifact_includes_halt_evidence_ref_and_invariant_context(tmp_path: Path) -> None:
    class DummyEpisode:
        def __init__(self) -> None:
            self.artifacts = []

    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    ep = DummyEpisode()

    gate = evaluate_invariant_gates(
        ep=ep,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        current_predictions={pred.scope_key: pred.prediction_id},
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": []},
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert gate.kind == "halt"
    assert len(ep.artifacts) == 1
    artifact = ep.artifacts[0]
    assert artifact["artifact_kind"] == "invariant_outcomes"
    assert artifact["kind"] == "halt"
    assert artifact["halt_evidence_ref"] == {"kind": "jsonl", "ref": "halts.jsonl@1"}
    assert artifact["invariant_context"]["prediction_log_available"] is True
    assert artifact["invariant_context"]["just_written_prediction"] == {
        "key": pred.scope_key,
        "evidence_refs": [],
    }


def test_append_prediction_and_projection_support_post_write_gate(tmp_path: Path) -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    evidence = append_prediction_record(pred, prediction_log_path=tmp_path / "predictions.jsonl")

    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    gate = evaluate_invariant_gates(
        ep=None,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        current_predictions=projected.current_predictions,
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": [evidence]},
    )

    assert evidence["ref"].startswith("predictions.jsonl@")
    assert projected.current_predictions[pred.scope_key] == pred.prediction_id
    assert gate.kind == "prediction"
    assert gate.halt is None
    assert gate.post_write[0].code == "prediction_write_materialized"
