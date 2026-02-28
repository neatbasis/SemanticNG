from __future__ import annotations

from pathlib import Path

from state_renormalization.adapters.persistence import read_jsonl
from collections.abc import Callable

from state_renormalization.contracts import AskResult, AskStatus, BeliefState, Episode, PredictionRecord, ProjectionState
from state_renormalization.engine import replay_projection_analytics, run_mission_loop


FIXED_PREDICTION = {
    "prediction_id": "pred:base",
    "scope_key": "turn:1",
    "prediction_key": "turn:1:user_response_present",
    "prediction_target": "user_response_present",
    "filtration_id": "conversation:c1",
    "target_variable": "user_response_present",
    "target_horizon_iso": "2026-02-13T00:00:00+00:00",
    "expectation": 0.75,
    "issued_at_iso": "2026-02-13T00:00:00+00:00",
}


def test_replay_projection_analytics_is_deterministic_across_repeated_runs(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "predictions.jsonl"
    ep = make_episode(
        conversation_id="conv:replay",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="yes"),
    )
    projection = ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")

    _, _, online_projection = run_mission_loop(
        ep,
        BeliefState(),
        projection,
        pending_predictions=[PredictionRecord.model_validate(FIXED_PREDICTION)],
        prediction_log_path=log_path,
    )

    replay_a = replay_projection_analytics(log_path)
    replay_b = replay_projection_analytics(log_path)

    assert replay_a.model_dump(mode="json") == replay_b.model_dump(mode="json")
    assert replay_a.records_processed == 3
    assert replay_a.projection_state.current_predictions.keys() == online_projection.current_predictions.keys()
    assert replay_a.projection_state.correction_metrics["comparisons"] == online_projection.correction_metrics["comparisons"]


def test_replay_projection_analytics_exposes_correction_lineage_from_append_only_log(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "predictions.jsonl"
    ep = make_episode(
        conversation_id="conv:lineage",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="affirmative"),
    )
    projection = ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")

    run_mission_loop(
        ep,
        BeliefState(),
        projection,
        pending_predictions=[PredictionRecord.model_validate(FIXED_PREDICTION)],
        prediction_log_path=log_path,
    )

    replay = replay_projection_analytics(log_path)
    replayed = replay.projection_state.current_predictions["turn:1"]

    assert replayed.was_corrected is True
    assert replayed.correction_parent_prediction_id == replayed.prediction_id
    assert replayed.correction_root_prediction_id == replayed.prediction_id
    assert replayed.correction_revision == 1

    rows = [record for _, record in read_jsonl(log_path)]
    corrected_rows = [row for row in rows if row.get("scope_key") == "turn:1" and row.get("was_corrected")]
    assert corrected_rows[-1]["correction_root_prediction_id"] == "pred:base"
