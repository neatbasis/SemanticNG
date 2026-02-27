from __future__ import annotations

from pathlib import Path

from state_renormalization.contracts import HaltRecord, PredictionRecord, ProjectionState
from state_renormalization.adapters.persistence import read_jsonl
from state_renormalization.engine import PredictionOutcome, append_prediction_record, evaluate_invariant_gates, project_current


FIXED_PREDICTION = {
    "prediction_id": "pred:test",
    "prediction_key": "room:kitchen:light",
    "scope_key": "room:kitchen:light",
    "filtration_ref": "filt:1",
    "variable": "light_on",
    "horizon_iso": "2026-02-13T00:05:00+00:00",
    "distribution_kind": "bernoulli",
    "distribution_params": {"p": 0.7},
    "confidence": 0.88,
    "uncertainty": 0.12,
    "issued_at_iso": "2026-02-13T00:00:00+00:00",
    "valid_from_iso": "2026-02-13T00:00:00+00:00",
    "valid_until_iso": "2026-02-13T00:10:00+00:00",
    "stopping_time_iso": None,
    "invariants_assumed": ["prediction_availability.v1"],
    "evidence_links": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
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
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    gate = evaluate_invariant_gates(
        ep=None,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={
            "key": pred.scope_key,
            "evidence_refs": [e.model_dump(mode="json") for e in pred.evidence_links],
        },
    )

    assert isinstance(gate, PredictionOutcome)
    assert gate.post_write
    assert gate.post_write[0].code == "prediction_write_materialized"


def test_post_write_gate_halts_when_append_evidence_missing(tmp_path: Path) -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    gate = evaluate_invariant_gates(
        ep=None,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": []},
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert isinstance(gate, HaltRecord)
    assert gate.stage == "post_write"
    assert gate.violated_invariant_id == "prediction_retrievability.v1"
    assert gate.reason == "Prediction append did not produce retrievable evidence."
    assert [e.model_dump(mode="json") for e in gate.evidence_refs] == [{"kind": "scope", "ref": pred.scope_key}]
    assert gate.retryability is True


def test_halt_artifact_includes_halt_evidence_ref_and_invariant_context(tmp_path: Path) -> None:
    class DummyEpisode:
        def __init__(self) -> None:
            self.artifacts = []

    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )
    ep = DummyEpisode()

    gate = evaluate_invariant_gates(
        ep=ep,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": []},
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert isinstance(gate, HaltRecord)
    assert len(ep.artifacts) == 2
    artifact = ep.artifacts[0]
    assert artifact["artifact_kind"] == "invariant_outcomes"
    assert artifact["kind"] == "halt"
    assert artifact["halt"]["stable_halt_id"].startswith("halt:")
    assert artifact["halt_evidence_ref"] == {"kind": "jsonl", "ref": "halts.jsonl@1"}
    assert artifact["invariant_context"]["prediction_log_available"] is True
    assert artifact["invariant_context"]["has_current_predictions"] is True
    assert artifact["invariant_context"]["just_written_prediction"] == {
        "key": pred.scope_key,
        "evidence_refs": [],
    }
    assert artifact["invariant_checks"] == [
        {
            "gate_point": "pre_consume",
            "invariant_id": "prediction_availability.v1",
            "passed": True,
            "evidence": [],
            "reason": "current_prediction_available",
        },
        {
            "gate_point": "post_write",
            "invariant_id": "prediction_retrievability.v1",
            "passed": False,
            "evidence": [{"kind": "scope", "ref": pred.scope_key}],
            "reason": "Prediction append did not produce retrievable evidence.",
        },
        {
            "gate_point": "halt_validation",
            "invariant_id": "explainable_halt_completeness.v1",
            "passed": True,
            "evidence": [],
            "reason": "halt_explainable",
        },
    ]

    halt_observation = ep.artifacts[1]
    assert halt_observation["artifact_kind"] == "halt_observation"
    assert halt_observation["observation_type"] == "halt"
    assert halt_observation["stable_halt_id"].startswith("halt:")
    assert halt_observation["violated_invariant_id"] == "prediction_retrievability.v1"


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
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": [evidence]},
    )

    assert evidence["ref"].startswith("predictions.jsonl@")
    assert projected.current_predictions[pred.scope_key] == pred
    assert isinstance(gate, PredictionOutcome)
    assert gate.post_write[0].code == "prediction_write_materialized"


def test_pre_consume_gate_halts_without_any_projected_predictions(tmp_path: Path) -> None:
    gate = evaluate_invariant_gates(
        ep=None,
        scope="scope:test",
        prediction_key="scope:test",
        projection_state=ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
        prediction_log_available=True,
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert isinstance(gate, HaltRecord)
    assert gate.violated_invariant_id == "prediction_availability.v1"
    assert gate.reason == "Action selection requires at least one projected current prediction."


def test_append_prediction_record_persists_supplied_stable_ids(tmp_path: Path) -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    prediction_path = tmp_path / "predictions.jsonl"

    append_prediction_record(
        pred,
        prediction_log_path=prediction_path,
        stable_ids={"feature_id": "feat_1", "scenario_id": "scn_1", "step_id": "stp_1"},
    )

    (_, rec), = list(read_jsonl(prediction_path))
    assert rec["feature_id"] == "feat_1"
    assert rec["scenario_id"] == "scn_1"
    assert rec["step_id"] == "stp_1"


def test_evaluate_invariant_gates_persists_halt_with_episode_stable_ids(tmp_path: Path) -> None:
    class DummyEpisode:
        def __init__(self) -> None:
            self.artifacts = [{"kind": "stable_ids", "feature_id": "feat_1", "scenario_id": "scn_1", "step_id": "stp_1"}]

    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    evaluate_invariant_gates(
        ep=DummyEpisode(),
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": []},
        halt_log_path=tmp_path / "halts.jsonl",
    )

    (_, rec), = list(read_jsonl(tmp_path / "halts.jsonl"))
    assert rec["feature_id"] == "feat_1"
    assert rec["scenario_id"] == "scn_1"
    assert rec["step_id"] == "stp_1"
