from __future__ import annotations

from pathlib import Path

from state_renormalization.contracts import AskStatus, BeliefState, PredictionRecord, ProjectionState
from state_renormalization.engine import run_mission_loop
from state_renormalization.invariants import InvariantHandlingMode


def _seed_projection() -> ProjectionState:
    pred = PredictionRecord.model_validate(
        {
            "prediction_id": "pred:seed",
            "scope_key": "turn:0",
            "prediction_key": "turn:0:user_response_present",
            "prediction_target": "user_response_present",
            "filtration_id": "conversation:c1",
            "target_variable": "user_response_present",
            "target_horizon_iso": "2026-02-13T00:00:00+00:00",
            "expectation": 0.0,
            "issued_at_iso": "2026-02-13T00:00:00+00:00",
        }
    )
    return ProjectionState(current_predictions={pred.scope_key: pred}, prediction_history=[pred], updated_at_iso=pred.issued_at_iso)


def test_repair_mode_keeps_latest_projection_across_multiple_turns(make_episode, make_ask_result, tmp_path: Path) -> None:
    prediction_log = tmp_path / "predictions.jsonl"
    projection = _seed_projection()
    belief = BeliefState()

    first = make_episode(conversation_id="conv:multi", turn_index=1, ask=make_ask_result(status=AskStatus.OK, sentence="yes"))
    _, belief, projection = run_mission_loop(
        first,
        belief,
        projection,
        pending_predictions=[],
        prediction_log_path=prediction_log,
        invariant_handling_mode=InvariantHandlingMode.REPAIR_EVENTS,
    )

    second = make_episode(conversation_id="conv:multi", turn_index=2, ask=make_ask_result(status=AskStatus.NO_RESPONSE, sentence=None))
    _, _, projection = run_mission_loop(
        second,
        belief,
        projection,
        pending_predictions=[],
        prediction_log_path=prediction_log,
        invariant_handling_mode=InvariantHandlingMode.REPAIR_EVENTS,
    )

    assert "turn:2" in projection.current_predictions
    assert projection.correction_metrics["comparisons"] >= 2.0
    assert projection.prediction_history[-1].scope_key == "turn:2"
