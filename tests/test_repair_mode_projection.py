from __future__ import annotations

import json
from pathlib import Path

from state_renormalization.contracts import (
    AskStatus,
    BeliefState,
    Episode,
    PredictionRecord,
    ProjectionState,
)
from state_renormalization.engine import replay_projection_analytics, run_mission_loop
from state_renormalization.invariants import InvariantHandlingMode

FIXED_PENDING_PREDICTION = {
    "prediction_id": "pred:repair-base",
    "scope_key": "turn:1",
    "prediction_key": "turn:1:user_response_present",
    "prediction_target": "user_response_present",
    "filtration_id": "conversation:c1",
    "target_variable": "user_response_present",
    "target_horizon_iso": "2026-02-13T00:00:00+00:00",
    "expectation": 0.25,
    "issued_at_iso": "2026-02-13T00:00:00+00:00",
}


def _seed_projection() -> ProjectionState:
    pred = PredictionRecord.model_validate(FIXED_PENDING_PREDICTION)
    return ProjectionState(
        current_predictions={pred.scope_key: pred},
        prediction_history=[pred],
        updated_at_iso="2026-02-13T00:00:00+00:00",
    )


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_repair_mode_emits_repair_events_and_replay_applies_acceptance(
    make_episode,
    make_ask_result,
    tmp_path: Path,
) -> None:
    prediction_log = tmp_path / "predictions.jsonl"
    ep: Episode = make_episode(
        conversation_id="conv:repair",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="yes"),
    )

    _, _, live_projection = run_mission_loop(
        ep,
        BeliefState(),
        _seed_projection(),
        pending_predictions=[],
        prediction_log_path=prediction_log,
        invariant_handling_mode=InvariantHandlingMode.REPAIR_EVENTS,
    )

    rows = _read_jsonl(prediction_log)
    assert any(row.get("event_kind") == "repair_proposal" for row in rows)
    assert any(
        row.get("event_kind") == "repair_resolution" and row.get("decision") == "accepted"
        for row in rows
    )

    replay = replay_projection_analytics(prediction_log)
    assert (
        replay.projection_state.current_predictions.keys()
        == live_projection.current_predictions.keys()
    )
    assert replay.projection_state.correction_metrics == live_projection.correction_metrics


def test_repair_event_replay_deterministic_across_restart_branches(tmp_path: Path) -> None:
    seed_log = tmp_path / "seed.jsonl"
    seed_log.write_text(
        "\n".join(
            [
                '{"event_kind":"prediction_record","prediction_id":"pred:1","scope_key":"turn:1","filtration_id":"conversation:c1","target_variable":"user_response_present","target_horizon_iso":"2026-02-13T00:00:00+00:00","expectation":0.2,"issued_at_iso":"2026-02-13T00:00:00+00:00"}',
                '{"event_kind":"repair_proposal","repair_id":"repair:1","proposed_at_iso":"2026-02-13T00:00:01+00:00","reason":"proposal","invariant_id":"prediction_outcome_binding.v1","lineage_ref":{"scope_key":"turn:1","prediction_id":"pred:1","correction_root_prediction_id":"pred:1"},"proposed_prediction":{"prediction_id":"pred:1","scope_key":"turn:1","filtration_id":"conversation:c1","target_variable":"user_response_present","target_horizon_iso":"2026-02-13T00:00:00+00:00","expectation":0.2,"observed_value":1.0,"prediction_error":0.8,"absolute_error":0.8,"was_corrected":true,"correction_parent_prediction_id":"pred:1","correction_root_prediction_id":"pred:1","correction_revision":1,"issued_at_iso":"2026-02-13T00:00:00+00:00","compared_at_iso":"2026-02-13T00:00:01+00:00","corrected_at_iso":"2026-02-13T00:00:01+00:00"},"prediction_outcome":{"prediction_id":"pred:1","observed_outcome":1.0,"error_metric":0.8,"absolute_error":0.8,"recorded_at_iso":"2026-02-13T00:00:01+00:00"}}',
                '{"event_kind":"repair_resolution","repair_id":"repair:1","proposal_event_kind":"repair_proposal","decision":"accepted","resolved_at_iso":"2026-02-13T00:00:01+00:00","lineage_ref":{"scope_key":"turn:1","prediction_id":"pred:1","correction_root_prediction_id":"pred:1"},"accepted_prediction":{"prediction_id":"pred:1","scope_key":"turn:1","filtration_id":"conversation:c1","target_variable":"user_response_present","target_horizon_iso":"2026-02-13T00:00:00+00:00","expectation":0.2,"observed_value":1.0,"prediction_error":0.8,"absolute_error":0.8,"was_corrected":true,"correction_parent_prediction_id":"pred:1","correction_root_prediction_id":"pred:1","correction_revision":1,"issued_at_iso":"2026-02-13T00:00:00+00:00","compared_at_iso":"2026-02-13T00:00:01+00:00","corrected_at_iso":"2026-02-13T00:00:01+00:00"}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    branch_a = tmp_path / "branch-a.jsonl"
    branch_b = tmp_path / "branch-b.jsonl"
    payload = seed_log.read_text(encoding="utf-8")
    branch_a.write_text(payload, encoding="utf-8")
    branch_b.write_text(payload, encoding="utf-8")

    replay_a = replay_projection_analytics(branch_a)
    replay_b = replay_projection_analytics(branch_b)

    assert replay_a.model_dump(mode="json") == replay_b.model_dump(mode="json")
    assert replay_a.records_processed == 2
