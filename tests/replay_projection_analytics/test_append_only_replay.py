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


def _blank_projection() -> ProjectionState:
    return ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")


def test_append_only_replay_reconstructs_projection_state_deterministically(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    prediction_log = tmp_path / "predictions.jsonl"
    episode = make_episode(
        conversation_id="conv:append-only-rebuild",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="confirmed"),
    )

    _, _, online_projection = run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
        pending_predictions=[PredictionRecord.model_validate(FIXED_PENDING_PREDICTION)],
        prediction_log_path=prediction_log,
    )

    replay_once = replay_projection_analytics(prediction_log)
    replay_twice = replay_projection_analytics(prediction_log)

    assert replay_once.model_dump(mode="json") == replay_twice.model_dump(mode="json")
    assert replay_once.projection_state.current_predictions.keys() == online_projection.current_predictions.keys()
    assert replay_once.projection_state.correction_metrics == online_projection.correction_metrics


def test_append_only_replay_is_deterministic_across_simulated_restart_runs(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    seed_log = tmp_path / "predictions.seed.jsonl"
    first_turn = make_episode(
        conversation_id="conv:restart-sim",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="first"),
    )

    _, _, projection_after_first_turn = run_mission_loop(
        first_turn,
        BeliefState(),
        _blank_projection(),
        pending_predictions=[PredictionRecord.model_validate(FIXED_PENDING_PREDICTION)],
        prediction_log_path=seed_log,
    )

    log_a = tmp_path / "predictions.restart-a.jsonl"
    log_b = tmp_path / "predictions.restart-b.jsonl"
    seed_contents = seed_log.read_text(encoding="utf-8")
    log_a.write_text(seed_contents, encoding="utf-8")
    log_b.write_text(seed_contents, encoding="utf-8")

    replay_projection_a = replay_projection_analytics(log_a).projection_state
    replay_projection_b = replay_projection_analytics(log_b).projection_state

    second_turn = make_episode(
        conversation_id="conv:restart-sim",
        turn_index=2,
        ask=make_ask_result(status=AskStatus.OK, sentence="second"),
    )
    _, _, restarted_a = run_mission_loop(
        second_turn,
        BeliefState(),
        replay_projection_a,
        pending_predictions=[],
        prediction_log_path=log_a,
    )
    _, _, restarted_b = run_mission_loop(
        second_turn,
        BeliefState(),
        replay_projection_b,
        pending_predictions=[],
        prediction_log_path=log_b,
    )

    assert projection_after_first_turn.correction_metrics == replay_projection_a.correction_metrics == replay_projection_b.correction_metrics
    assert restarted_a.current_predictions.keys() == restarted_b.current_predictions.keys()
    assert restarted_a.correction_metrics == restarted_b.correction_metrics


def test_halt_explainability_payload_fields_remain_intact_through_projection_replay(
    make_episode: Callable[..., Episode],
    make_observer,
    tmp_path: Path,
) -> None:
    episode_log = tmp_path / "episodes.jsonl"
    prediction_log = tmp_path / "predictions.jsonl"

    episode = make_episode(observer=make_observer(capabilities=["baseline.dialog"]))
    gate = evaluate_invariant_gates(
        ep=episode,
        scope="scope:halt-replay",
        prediction_key=None,
        projection_state=_blank_projection(),
        prediction_log_available=True,
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert isinstance(gate, HaltRecord)
    append_jsonl(episode_log, to_jsonable_episode(episode))

    _ = replay_projection_analytics(prediction_log)

    (_, persisted), = list(read_jsonl(episode_log))
    halt_payloads = [
        artifact
        for artifact in persisted["artifacts"]
        if artifact.get("artifact_kind") in {"authorization_issue", "halt_observation"}
    ]

    required = set(HaltRecord.required_explainability_fields())
    for payload in halt_payloads:
        canonical = HaltRecord.from_payload(payload).to_canonical_payload()
        assert required.issubset(canonical)


def test_append_only_replay_preserves_minimal_correction_lineage_for_analytics(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    prediction_log = tmp_path / "predictions.jsonl"
    episode = make_episode(
        conversation_id="conv:lineage-integrity",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="affirmative"),
    )

    run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
        pending_predictions=[PredictionRecord.model_validate(FIXED_PENDING_PREDICTION)],
        prediction_log_path=prediction_log,
    )

    result = replay_projection_analytics(prediction_log)
    replayed = result.projection_state.current_predictions["turn:1"]
    assert replayed.was_corrected is True
    assert replayed.correction_root_prediction_id == "pred:base"
    assert replayed.correction_parent_prediction_id == "pred:base"
    assert replayed.correction_revision == 1

    attribution = result.analytics_snapshot.correction_cost_attribution["pred:base"]
    assert attribution.correction_count == 1
    assert attribution.correction_cost_total == 0.25
