from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from state_renormalization.adapters.persistence import append_jsonl, read_jsonl
from state_renormalization.contracts import AskResult, AskStatus, BeliefState, Episode, HaltRecord, PredictionRecord, ProjectionState
from state_renormalization.engine import evaluate_invariant_gates, replay_projection_analytics, run_mission_loop, to_jsonable_episode


FIXED_PENDING_PREDICTION = {
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


def test_projection_replay_rebuilds_the_same_state_across_repeated_runs(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    prediction_log = tmp_path / "predictions.jsonl"
    ep = make_episode(
        conversation_id="conv:rebuild",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="confirmed"),
    )

    _, _, online_projection = run_mission_loop(
        ep,
        BeliefState(),
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
        pending_predictions=[PredictionRecord.model_validate(FIXED_PENDING_PREDICTION)],
        prediction_log_path=prediction_log,
    )

    replay_a = replay_projection_analytics(prediction_log)
    replay_b = replay_projection_analytics(prediction_log)

    assert replay_a.model_dump(mode="json") == replay_b.model_dump(mode="json")
    assert replay_a.projection_state.current_predictions.keys() == online_projection.current_predictions.keys()
    assert replay_a.projection_state.correction_metrics == online_projection.correction_metrics
    assert replay_a.records_processed == 3


def test_projection_replay_is_deterministic_after_restart_with_same_log(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    prediction_log = tmp_path / "predictions.jsonl"
    initial_projection = ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")

    ep1 = make_episode(
        conversation_id="conv:restart",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="first reply"),
    )
    _, _, online_after_turn_1 = run_mission_loop(
        ep1,
        BeliefState(),
        initial_projection,
        pending_predictions=[PredictionRecord.model_validate(FIXED_PENDING_PREDICTION)],
        prediction_log_path=prediction_log,
    )

    recovered_after_restart = replay_projection_analytics(prediction_log).projection_state
    assert recovered_after_restart.current_predictions.keys() == online_after_turn_1.current_predictions.keys()
    assert recovered_after_restart.correction_metrics == online_after_turn_1.correction_metrics

    ep2 = make_episode(
        conversation_id="conv:restart",
        turn_index=2,
        ask=make_ask_result(status=AskStatus.OK, sentence="second reply"),
    )
    _, _, online_after_turn_2 = run_mission_loop(
        ep2,
        BeliefState(),
        recovered_after_restart,
        pending_predictions=[],
        prediction_log_path=prediction_log,
    )

    replay_after_turn_2 = replay_projection_analytics(prediction_log)
    assert replay_after_turn_2.projection_state.current_predictions.keys() == online_after_turn_2.current_predictions.keys()
    assert replay_after_turn_2.projection_state.correction_metrics == online_after_turn_2.correction_metrics


def test_halt_artifacts_keep_explainability_fields_when_projection_is_replayed(
    make_episode: Callable[..., Episode],
    make_observer,
    tmp_path: Path,
) -> None:
    episode_log = tmp_path / "episodes.jsonl"
    prediction_log = tmp_path / "predictions.jsonl"

    ep = make_episode(observer=make_observer(capabilities=["baseline.dialog"]))
    gate = evaluate_invariant_gates(
        ep=ep,
        scope="scope:halt",
        prediction_key=None,
        projection_state=ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
        prediction_log_available=True,
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert isinstance(gate, HaltRecord)
    append_jsonl(episode_log, to_jsonable_episode(ep))

    # Trigger projection replay to ensure log-based rebuilding does not affect explainability payloads.
    _ = replay_projection_analytics(prediction_log)

    (_, persisted_episode), = list(read_jsonl(episode_log))
    halt_artifacts = [a for a in persisted_episode["artifacts"] if a.get("artifact_kind") in {"authorization_issue", "halt_observation"}]
    assert halt_artifacts

    required = set(HaltRecord.required_explainability_fields())
    for artifact in halt_artifacts:
        canonical = HaltRecord.from_payload(artifact).to_canonical_payload()
        assert required.issubset(canonical)


def test_replay_preserves_correction_lineage_fields_for_analytics(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    prediction_log = tmp_path / "predictions.jsonl"
    ep = make_episode(
        conversation_id="conv:lineage-analytics",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="affirmative"),
    )

    run_mission_loop(
        ep,
        BeliefState(),
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
        pending_predictions=[PredictionRecord.model_validate(FIXED_PENDING_PREDICTION)],
        prediction_log_path=prediction_log,
    )

    replayed_prediction = replay_projection_analytics(prediction_log).projection_state.current_predictions["turn:1"]
    assert replayed_prediction.was_corrected is True
    assert replayed_prediction.correction_root_prediction_id == "pred:base"
    assert replayed_prediction.correction_parent_prediction_id == "pred:base"
    assert replayed_prediction.correction_revision == 1

    rows = [row for _, row in read_jsonl(prediction_log) if row.get("event_kind") == "prediction_record"]
    corrected_rows = [row for row in rows if row.get("scope_key") == "turn:1" and row.get("was_corrected")]
    assert corrected_rows

    latest = corrected_rows[-1]
    assert latest["correction_root_prediction_id"] == "pred:base"
    assert latest["correction_parent_prediction_id"] == "pred:base"
    assert latest["correction_revision"] == 1
