from __future__ import annotations

from state_renormalization.contracts import PredictionOutcome, PredictionRecord
from state_renormalization.engine import bind_prediction_outcome
from state_renormalization.invariants import REGISTRY, InvariantId, default_check_context

FIXED_PREDICTION = {
    "prediction_id": "pred:1",
    "scope_key": "turn:1",
    "prediction_key": "turn:1:user_response_present",
    "prediction_target": "user_response_present",
    "filtration_id": "conversation:c1",
    "target_variable": "user_response_present",
    "target_horizon_iso": "2026-02-13T00:00:00+00:00",
    "expectation": 0.75,
    "issued_at_iso": "2026-02-13T00:00:00+00:00",
}


def test_prediction_outcome_contract_supports_recorded_at_alias() -> None:
    outcome = PredictionOutcome.model_validate(
        {
            "prediction_id": "pred:1",
            "observed_outcome": 1.0,
            "error_metric": 0.25,
            "absolute_error": 0.25,
            "recorded_at": "2026-02-13T00:01:00+00:00",
        }
    )

    assert outcome.recorded_at_iso == "2026-02-13T00:01:00+00:00"
    assert outcome.recorded_at == "2026-02-13T00:01:00+00:00"


def test_bind_prediction_outcome_updates_prediction_and_emits_contract() -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)

    updated, outcome = bind_prediction_outcome(
        pred,
        observed_outcome=1.0,
        recorded_at_iso="2026-02-13T00:01:00+00:00",
    )

    assert updated.observed_value == 1.0
    assert updated.prediction_error == 0.25
    assert updated.absolute_error == 0.25
    assert updated.was_corrected is True
    assert updated.correction_parent_prediction_id == pred.prediction_id
    assert updated.correction_root_prediction_id == pred.prediction_id
    assert updated.correction_revision == 1

    assert outcome.prediction_id == pred.prediction_id
    assert outcome.prediction_scope_key == pred.scope_key
    assert outcome.target_variable == pred.target_variable
    assert outcome.error_metric == 0.25
    assert outcome.absolute_error == 0.25


def test_prediction_outcome_binding_invariant_passes_for_bound_outcome() -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    _, outcome = bind_prediction_outcome(
        pred, observed_outcome=1.0, recorded_at_iso="2026-02-13T00:01:00+00:00"
    )

    ctx = default_check_context(
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        current_predictions={pred.scope_key: pred.model_dump(mode="json")},
        prediction_log_available=True,
        prediction_outcome=outcome.model_dump(mode="json"),
    )

    result = REGISTRY[InvariantId.PREDICTION_OUTCOME_BINDING](ctx)
    assert result.passed is True
    assert result.code == "prediction_outcome_bound"
