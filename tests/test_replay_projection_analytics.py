from __future__ import annotations

from pathlib import Path

from state_renormalization.adapters.persistence import append_jsonl, read_jsonl
from collections.abc import Callable

from state_renormalization.contracts import AskResult, AskStatus, BeliefState, Episode, HaltRecord, PredictionRecord, ProjectionState
from state_renormalization.engine import (
    derive_projection_analytics_from_lineage,
    evaluate_invariant_gates,
    replay_projection_analytics,
    run_mission_loop,
    to_jsonable_episode,
)


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
    assert replay_a.analytics_snapshot.correction_count == 1
    assert replay_a.analytics_snapshot.correction_cost_total == 0.25


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

    attribution = replay.analytics_snapshot.correction_cost_attribution["pred:base"]
    assert attribution.correction_count == 1
    assert attribution.correction_cost_total == 0.25


def test_replay_projection_analytics_snapshot_matches_for_independent_consumers(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "predictions.jsonl"
    ep = make_episode(
        conversation_id="conv:independent-consumers",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="yes"),
    )

    run_mission_loop(
        ep,
        BeliefState(),
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
        pending_predictions=[PredictionRecord.model_validate(FIXED_PREDICTION)],
        prediction_log_path=log_path,
    )

    consumer_a_snapshot = replay_projection_analytics(log_path).analytics_snapshot
    consumer_b_snapshot = replay_projection_analytics(log_path).analytics_snapshot

    assert consumer_a_snapshot.model_dump(mode="json") == consumer_b_snapshot.model_dump(mode="json")
    assert consumer_a_snapshot.correction_count == 1
    assert consumer_a_snapshot.correction_cost_total == 0.25
    assert consumer_a_snapshot.correction_cost_attribution["pred:base"].correction_count == 1


def test_halt_explainability_fields_survive_episode_persistence_roundtrip(
    make_episode: Callable[..., Episode],
    make_observer,
    tmp_path: Path,
) -> None:
    episode_path = tmp_path / "episodes.jsonl"

    ep = make_episode(observer=make_observer(capabilities=["baseline.dialog"]))
    gate = evaluate_invariant_gates(
        ep=ep,
        scope="scope:test",
        prediction_key=None,
        projection_state=ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
        prediction_log_available=True,
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert isinstance(gate, HaltRecord)
    expected = gate.to_canonical_payload()

    append_jsonl(episode_path, to_jsonable_episode(ep))
    (_, persisted), = list(read_jsonl(episode_path))

    authorization_issue = next(a for a in persisted["artifacts"] if a.get("artifact_kind") == "authorization_issue")
    halt_observation = next(a for a in persisted["artifacts"] if a.get("artifact_kind") == "halt_observation")
    (_, persisted_halt), = list(read_jsonl(tmp_path / "halts.jsonl"))

    assert HaltRecord.from_payload(authorization_issue).to_canonical_payload() == expected
    assert HaltRecord.from_payload(halt_observation).to_canonical_payload() == expected
    assert HaltRecord.from_payload(persisted_halt).to_canonical_payload() == expected
    assert set(expected).issuperset(HaltRecord.required_explainability_fields())


def test_derive_projection_analytics_from_lineage_is_deterministic_and_log_only() -> None:
    lineage = [
        {
            "event_kind": "prediction_record",
            "prediction_id": "pred:base",
            "scope_key": "turn:1",
            "filtration_id": "conversation:c1",
            "target_variable": "user_response_present",
            "target_horizon_iso": "2026-02-13T00:00:00+00:00",
            "issued_at_iso": "2026-02-13T00:00:00+00:00",
            "was_corrected": True,
            "absolute_error": 0.25,
            "correction_root_prediction_id": "pred:base",
            "correction_parent_prediction_id": "pred:base",
            "correction_revision": 1,
        },
        {
            "event_kind": "prediction_record",
            "prediction_id": "pred:child",
            "scope_key": "turn:2",
            "filtration_id": "conversation:c1",
            "target_variable": "user_response_present",
            "target_horizon_iso": "2026-02-14T00:00:00+00:00",
            "issued_at_iso": "2026-02-14T00:00:00+00:00",
            "was_corrected": True,
            "absolute_error": 0.5,
            "correction_root_prediction_id": "pred:base",
            "correction_parent_prediction_id": "pred:base",
            "correction_revision": 2,
        },
        {
            "halt_id": "halt:1",
            "stage": "gate:pre_consume",
            "invariant_id": "prediction_availability.v1",
            "reason": "missing prediction",
            "details": {"scope": "turn:3"},
            "evidence": [{"kind": "jsonl", "ref": "predictions.jsonl@4"}],
            "retryability": True,
            "timestamp": "2026-02-14T00:00:00+00:00",
        },
    ]

    first = derive_projection_analytics_from_lineage(lineage)
    second = derive_projection_analytics_from_lineage(lineage)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.correction_count == 2
    assert first.correction_cost_total == 0.75
    assert first.correction_cost_mean == 0.375
    assert first.halt_count == 1

    attributed = first.correction_cost_attribution["pred:base"]
    assert attributed.correction_count == 2
    assert attributed.correction_cost_total == 0.75


def test_derive_projection_analytics_from_lineage_ignores_non_lineage_rows() -> None:
    lineage = [
        {"event_kind": "turn_summary", "turn_index": 1},
        {
            "event_kind": "prediction_record",
            "prediction_id": "pred:x",
            "scope_key": "turn:x",
            "filtration_id": "conversation:c1",
            "target_variable": "user_response_present",
            "target_horizon_iso": "2026-02-13T00:00:00+00:00",
            "issued_at_iso": "2026-02-13T00:00:00+00:00",
            "was_corrected": False,
        },
    ]

    analytics = derive_projection_analytics_from_lineage(lineage)

    assert analytics.correction_count == 0
    assert analytics.correction_cost_total == 0.0
    assert analytics.halt_count == 0
    assert analytics.correction_cost_attribution == {}


def test_replay_projection_analytics_uses_lineage_iterator_and_ignores_runtime_only_rows(tmp_path: Path) -> None:
    log_path = tmp_path / "lineage.jsonl"
    append_jsonl(
        log_path,
        {
            "event_kind": "prediction_record",
            "prediction_id": "pred:a",
            "scope_key": "turn:1",
            "filtration_id": "conversation:c1",
            "target_variable": "user_response_present",
            "target_horizon_iso": "2026-02-13T00:00:00+00:00",
            "issued_at_iso": "2026-02-13T00:00:00+00:00",
            "was_corrected": True,
            "absolute_error": 0.2,
            "correction_root_prediction_id": "pred:a",
            "runtime_cache": {"not": "persisted-analytics-input"},
        },
    )
    append_jsonl(log_path, {"event_kind": "debug_runtime_state", "value": 99})

    replay = replay_projection_analytics(log_path)

    assert replay.records_processed == 1
    assert replay.analytics_snapshot.correction_count == 1
    assert replay.analytics_snapshot.correction_cost_total == 0.2


def test_derive_projection_analytics_from_lineage_tracks_human_request_views() -> None:
    lineage = [
        {
            "event_kind": "ask_outbox_request",
            "request_id": "ask:open",
            "scope": "after_invariants",
            "reason": "human recruitment requested by intervention lifecycle",
            "evidence_refs": [{"kind": "intervention_request", "ref": "hitl:open"}],
            "created_at_iso": "2026-02-14T00:00:00+00:00",
            "metadata": {"conversation_id": "conv:1"},
        },
        {
            "event_kind": "ask_outbox_request",
            "request_id": "ask:resolved",
            "scope": "after_invariants",
            "reason": "human recruitment requested by intervention lifecycle",
            "evidence_refs": [{"kind": "intervention_request", "ref": "hitl:resolved"}],
            "created_at_iso": "2026-02-14T00:01:00+00:00",
            "metadata": {"conversation_id": "conv:1"},
        },
        {
            "event_kind": "ask_outbox_response",
            "request_id": "ask:resolved",
            "scope": "after_invariants",
            "reason": "intervention decision recorded",
            "evidence_refs": [{"kind": "intervention_request", "ref": "hitl:resolved"}],
            "created_at_iso": "2026-02-14T00:01:00+00:00",
            "responded_at_iso": "2026-02-14T00:02:00+00:00",
            "status": "resume",
            "escalation": False,
            "metadata": {"operator": "alice"},
        },
    ]

    snapshot = derive_projection_analytics_from_lineage(lineage)

    assert set(snapshot.outstanding_human_requests.keys()) == {"ask:open"}
    assert set(snapshot.resolved_human_requests.keys()) == {"ask:resolved"}
    assert snapshot.request_outcome_linkage == {"ask:resolved": "resume"}
