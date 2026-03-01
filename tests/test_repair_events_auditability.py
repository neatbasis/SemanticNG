from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from state_renormalization.contracts import (
    AskStatus,
    BeliefState,
    Episode,
    PredictionRecord,
    ProjectionState,
    RepairProposalEvent,
)
from state_renormalization.engine import run_mission_loop
from state_renormalization.invariants import InvariantHandlingMode

FIXED_PENDING_PREDICTION = {
    "prediction_id": "pred:audit-base",
    "scope_key": "turn:1",
    "prediction_key": "turn:1:user_response_present",
    "prediction_target": "user_response_present",
    "filtration_id": "conversation:c1",
    "target_variable": "user_response_present",
    "target_horizon_iso": "2026-02-13T00:00:00+00:00",
    "expectation": 0.1,
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


def test_repair_events_are_lineage_traceable_and_immutable(
    make_episode,
    make_ask_result,
    tmp_path: Path,
) -> None:
    prediction_log = tmp_path / "predictions.jsonl"
    ep: Episode = make_episode(
        conversation_id="conv:audit",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="ack"),
    )

    run_mission_loop(
        ep,
        BeliefState(),
        _seed_projection(),
        pending_predictions=[],
        prediction_log_path=prediction_log,
        invariant_handling_mode=InvariantHandlingMode.REPAIR_EVENTS,
    )

    rows = _read_jsonl(prediction_log)
    proposal_row = next(row for row in rows if row.get("event_kind") == "repair_proposal")
    resolution_row = next(row for row in rows if row.get("event_kind") == "repair_resolution")

    assert proposal_row["lineage_ref"]["scope_key"] == "turn:1"
    prediction_ids = {
        row.get("prediction_id") for row in rows if row.get("event_kind") == "prediction_record"
    }
    assert proposal_row["lineage_ref"]["prediction_id"] in prediction_ids
    assert resolution_row["lineage_ref"] == proposal_row["lineage_ref"]

    proposal = RepairProposalEvent.model_validate(proposal_row)
    try:
        proposal.repair_id = "repair:tamper"
    except ValidationError:
        pass
    else:
        raise AssertionError("repair proposal events must be immutable")


def test_repair_mode_does_not_silently_mutate_prediction_records(
    make_episode,
    make_ask_result,
    tmp_path: Path,
) -> None:
    prediction_log = tmp_path / "predictions.jsonl"
    ep: Episode = make_episode(
        conversation_id="conv:audit-nomutation",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="ack"),
    )

    run_mission_loop(
        ep,
        BeliefState(),
        _seed_projection(),
        pending_predictions=[],
        prediction_log_path=prediction_log,
        invariant_handling_mode=InvariantHandlingMode.REPAIR_EVENTS,
    )

    rows = _read_jsonl(prediction_log)
    corrected_prediction_records = [
        row
        for row in rows
        if row.get("event_kind") == "prediction_record"
        and int(row.get("correction_revision") or 0) > 0
    ]
    assert corrected_prediction_records == []

    accepted_resolutions = [
        row
        for row in rows
        if row.get("event_kind") == "repair_resolution" and row.get("decision") == "accepted"
    ]
    assert accepted_resolutions
    assert all(
        int((row.get("accepted_prediction") or {}).get("correction_revision") or 0) > 0
        for row in accepted_resolutions
    )
